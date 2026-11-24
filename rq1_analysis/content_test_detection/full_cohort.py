from github_http import GitHubLowQuota,read_count
"""Bounded full-cohort expansion; all writes stay in outputs/full_cohort/."""
import argparse,json,os,math,time
from pathlib import Path
import pandas as pd
import portalocker
import scale100 as engine
import grok
import cohort_overlay
from common import BASE,HERE,OUT,CACHE,KEY,stable_hash,sha256,write_json,protect_prior
from detector import eligible

DEST=OUT/'full_cohort'
BATCH='batch_0001'

def freeze_inputs():
    d=DEST/'inputs';d.mkdir(parents=True,exist_ok=True)
    for name in ['reconciled_main_outcomes.csv','reconciled_inspection_audit.csv','pr_outcomes.csv','inspection_audit.csv','summary.json','api_usage.json']:
        source=OUT/'scale100'/name;target=d/name
        if not target.exists():target.write_bytes(source.read_bytes())
    main=pd.read_csv(d/'reconciled_main_outcomes.csv');latest=pd.read_csv(d/'pr_outcomes.csv')
    # Supplement stale reconciliation with latest completed 100-PR outcomes.
    for r in latest.to_dict('records'):
        if pd.notna(r['test_added_content_verified']):
            mask=main.repo_name.eq(r['repo_name'])&main.pr_number.eq(r['pr_number'])
            for k,v in r.items():
                if k not in main:main[k]=None
                main.loc[mask,k]=v
    main.to_csv(DEST/'entry_cohort.csv',index=False)
    return main

def make_queue(entry,n=500):
    queue_path=DEST/'unresolved_queue.csv';sample_path=DEST/BATCH/'sample.csv';sample_path.parent.mkdir(exist_ok=True)
    if sample_path.exists():return pd.read_csv(queue_path),pd.read_csv(sample_path)
    main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    unknown=set(map(tuple,entry.loc[entry.test_added_content_verified.isna(),KEY].to_numpy()))
    pool=main[[tuple(k) in unknown for k in main[KEY].to_numpy()]].copy()
    previous=set()
    for prior in DEST.glob('batch_*/sample.csv'):
        if prior!=sample_path:previous.update(map(tuple,pd.read_csv(prior)[KEY].to_numpy()))
    pool=pool[[tuple(k) not in previous for k in pool[KEY].to_numpy()]].copy()
    pool['stratum']=pool.tool.astype(str)+'|AC='+pool.has_acceptance_criteria.astype(str)+'|EC='+pool.has_edge_cases.astype(str)
    pool['selection_hash']=[stable_hash(f'full-cohort-v1|{r}|{p}') for r,p in pool[KEY].to_numpy()]
    pool=pool.sort_values('selection_hash');pool['within_stratum_rank']=pool.groupby('stratum').cumcount()+1
    sizes=pool.groupby('stratum').size();n=min(n,len(pool));alloc=(sizes*n/len(pool)).apply(math.floor)
    for key in (sizes*n/len(pool)-alloc).sort_values(ascending=False,kind='stable').index[:n-int(alloc.sum())]:alloc[key]+=1
    pool['eligible_stratum_n']=pool.stratum.map(sizes);pool['allocated_batch_n']=pool.stratum.map(alloc)
    pool['batch_inclusion_fraction']=pool.allocated_batch_n/pool.eligible_stratum_n
    pool['queue_priority']=pool.within_stratum_rank/pool.eligible_stratum_n
    queue=pool.sort_values(['queue_priority','selection_hash']).copy();queue['queue_rank']=range(1,len(queue)+1)
    sample=queue[queue.within_stratum_rank.le(queue.allocated_batch_n)].copy()
    # Selection is proportional by stratum; repository rotation changes execution
    # order only, never which observations are selected.
    sample=sample.sort_values('selection_hash');sample['repo_execution_round']=sample.groupby('repo_name').cumcount()
    sample=sample.sort_values(['repo_execution_round','queue_priority','selection_hash']);sample['execution_rank']=range(1,len(sample)+1)
    if not queue_path.exists():queue.to_csv(queue_path,index=False)
    sample.to_csv(sample_path,index=False)
    write_json(DEST/BATCH/'selection_protocol.json',{'version':'full-cohort-v1','seed_domain':'full-cohort-v1|repo|PR','eligible_n':len(pool),'batch_n':len(sample),'allocation':'proportional largest remainder by tool/snapshot AC/snapshot EC; stable hash within stratum','execution_order':'repository rotation, then proportional queue priority','warning':'Pseudo-random reproducible draw; finite selected cohort only. Inclusion fractions describe assigned draw, not completion or population sampling. No inference weight corrects retrieval bias.'})
    return queue,sample

def groups():
    raw=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=KEY+['file_path','change_status'])
    return {k:g for k,g in raw.groupby(KEY)}

def estimate(sample,rawgroups,args):
    n=sum(sum(r.change_status=='added' and eligible(r.file_path) for r in rawgroups[tuple(key)].itertuples()) for key in sample[KEY].to_numpy())
    used=read_count(CACHE);ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts']
    return {'selected_prs':len(sample),'repositories':sample.repo_name.nunique(),'tool_counts':sample.tool.value_counts().to_dict(),'worst_case_metadata':len(sample),'worst_case_file_pages':int(((sample.n_files+99)//100).sum()),'eligible_added_source_files':n,'grok_calls_range':[0,n],'lifetime_grok_cap':args.max_grok_requests,'lifetime_grok_attempts':len(ledger),'spend_ceiling_usd':args.max_grok_spend,'actual_cost_usd':sum(r.get('reported_cost_usd',0) for r in ledger),'github_cached_reads_used':used,'cumulative_github_cap':args.github_limit,'github_reads_available_in_cap':max(0,args.github_limit-used),'per_10k_input_1200_output_call_cost_usd':.0155,'note':'Upper bounds before early stopping/cache reuse. Actual authenticated quota unavailable until a live response; cache count is an acquisition cap, not API quota.'}


def needs_processing(path,live=False,retry_unknown=False):
    if not path.exists():return True
    old=pd.read_csv(path)
    if old.test_added_content_verified.notna().all():return False
    return live or retry_unknown


def resource_block_reason(state,github_remaining,fetch_enabled,model_available):
    if state in {'not_yet_examined','waiting_github_content'}:
        if not fetch_enabled:return 'github_acquisition_not_enabled'
        if github_remaining<=0:return 'github_cumulative_limit'
    if state=='waiting_grok_classification' and not model_available:return 'model_requests_disabled_or_unavailable'
    return None


def prioritize_remaining(sample,states):
    """Change execution order only; keep frozen inclusion/ranks untouched."""
    by_key={tuple(r[k] for k in KEY):r for r in states.to_dict('records')}
    def cost(row):
        state=by_key.get(tuple(row[k] for k in KEY),{})
        category=state.get('verification_state','not_yet_examined')
        details=json.loads(state.get('details','[]'))
        model_files=sum(isinstance(d,dict) and d.get('model_status') in {
            'dry_run','missing_XAI_API_KEY'} for d in details)
        rank={'cache_ready_for_replay':0,'waiting_grok_classification':1,'waiting_github_content':2,'not_yet_examined':3}.get(category,4)
        if category=='waiting_grok_classification' and len(details)>model_files:
            # A negative model result cannot finish a PR with an independent blocker.
            rank=4
        return (rank,model_files,row.get('n_files',0),row.get('execution_rank',0))
    rows=sample.to_dict('records')
    return pd.DataFrame(sorted(rows,key=cost))


def add_model_limits(parser):
    parser.add_argument('--max-grok-spend', type=float, default=3.0,
                        help='Cumulative USD limit including prior charges and reservations (maximum $7)')
    parser.add_argument('--max-grok-requests', type=int, default=100,
                        help='Cumulative attempt limit including prior attempts (maximum 1000)')
    parser.add_argument('--max-new-model-calls', type=int, default=10,
                        help='New attempts per run, including provider retries (maximum 100)')


def validate_model_limits(parser, args):
    if not 0 <= args.max_grok_spend <= engine.ScalingBudget.max_authorized_spend:
        parser.error('--max-grok-spend must be between 0 and 7')
    if not 0 <= args.max_grok_requests <= 1000:
        parser.error('--max-grok-requests must be between 0 and 1000')
    if not 0 <= args.max_new_model_calls <= 100:
        parser.error('--max-new-model-calls must be between 0 and 100')


def quality_circuit_path(directory, rearm=False):
    original = directory / f'circuit_state_{grok.PROMPT_VERSION}.json'
    trial = original.with_suffix(f'.rearm-{grok.VALIDATOR_VERSION}.json')
    # The new window survives restarts, including a second --rearm request.
    if rearm and not trial.exists():
        write_json(trial, [], immutable=True)
    return trial if trial.exists() else original


def evidence_v5_circuit_path(directory):
    return directory/f'circuit_state_{grok.EVIDENCE_V5}.json'


def resource_status(args,resolver):
    rows=resolver.budget.state['attempts'];used=read_count(CACHE)
    reserved=sum(row['charged_or_reserved_usd'] for row in rows)
    run_remaining=max(0,resolver.budget.max_requests-len(rows))
    model_enabled=(args.live and not args.deterministic_only and not resolver.model_disabled
                   and not resolver.transport_blocked and run_remaining>0
                   and reserved<resolver.budget.max_spend)
    return {'github_used':used,'github_cumulative_limit':args.github_limit,'github_remaining':max(0,args.github_limit-used),'github_acquisition_enabled':args.fetch_github,'github_hourly_quota':'See last response headers; independent of local cumulative cap','grok_lifetime_attempts':len(rows),'grok_lifetime_limit':args.max_grok_requests,'grok_lifetime_remaining':max(0,args.max_grok_requests-len(rows)),'grok_current_run_remaining':run_remaining,'grok_spend_ceiling_usd':resolver.budget.max_spend,'grok_charged_or_reserved_usd':reserved,'grok_spend_remaining_usd':max(0,resolver.budget.max_spend-reserved),'grok_quality_fallback':resolver.model_disabled,'grok_transport_blocked_invalid_argument':resolver.transport_blocked,'grok_requests_enabled':model_enabled}


def protect_selection():
    manifest=DEST/BATCH/'selection_integrity.json'
    files=[DEST/BATCH/'sample.csv',DEST/'unresolved_queue.csv']+list((DEST/'inputs').glob('*'))
    hashes={str(p.relative_to(DEST)):sha256(p.read_bytes()) for p in files}
    if manifest.exists():
        if json.loads(manifest.read_text())!=hashes:raise RuntimeError('Frozen selection/input integrity mismatch')
    else:write_json(manifest,hashes,immutable=True)

def runner_delta():
    base = cohort_overlay.read_delta(DEST)
    pending = DEST/cohort_overlay.VERSION/'ai-assisted-source-v1'
    if (pending/'resolved').is_dir():
        from ai_assisted import published_delta
        additions = published_delta(pending)
        if not additions.empty:
            return pd.concat([base,additions],ignore_index=True)
    return base

def publish(entry,sample):
    frames=[];audits=[]
    all_frames=[pd.read_csv(p) for p in sorted(DEST.glob('batch_*/results/*.csv'))]
    for path in sorted((DEST/BATCH/'results').glob('*.csv')):frames.append(pd.read_csv(path))
    for path in sorted((DEST/BATCH/'audits').glob('*.csv')):
        try:audits.append(pd.read_csv(path))
        except pd.errors.EmptyDataError:pass
    done=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=KEY+['test_added_content_verified'])
    delta=runner_delta()
    checkpoint_count=len(done)
    if not delta.empty:
        active=sample[KEY].merge(delta,on=KEY,validate='one_to_one')
        done=cohort_overlay.apply_delta(done,active)
        missing=active.merge(done[KEY],on=KEY,how='left',indicator=True)
        missing=missing[missing['_merge'].eq('left_only')].drop(columns='_merge')
        if not missing.empty:
            done=pd.concat([done,missing],ignore_index=True)
    merged=entry.set_index(KEY).copy()
    combined=pd.concat(all_frames,ignore_index=True).drop_duplicates(KEY,keep='last') if all_frames else done
    for r in combined.to_dict('records'):
        k=tuple(r[x] for x in KEY)
        for col,value in r.items():
            if col in KEY:continue
            if col not in merged:merged[col]=None
            merged.loc[k,col]=value
    corrections=DEST/'known_negative_corrections.json'
    if corrections.exists():
        from storage import Store,metadata_request
        for r in json.loads(corrections.read_text()):
            key=tuple(r[k] for k in KEY);assert r['test_added_content_verified']==1
            store=Store();metadata=store.data(metadata_request(*key));assert metadata['head_sha']==r['pinned_commit_sha']
            files,complete,_,_=store.files(*key);assert complete
            changed=next(file for file in files if file['filename']==r['confirmed_file_path'] and file['status']=='added')
            text,provenance,_=store.content(key[0],metadata['head_sha'],changed['filename'],changed.get('sha'))
            assert text is not None and provenance['content_sha256']==r['file_content_hash']
            for col,value in r.items():
                if col in KEY:continue
                if col not in merged:merged[col]=None
                merged.loc[key,col]=value
    merged=merged.reset_index()
    merged=cohort_overlay.apply_delta(merged,delta,require_membership=True)
    cohort_overlay.atomic_csv(DEST/'current_main_outcomes.csv',merged)
    batch=sample.merge(done,on=KEY,how='left',suffixes=('_selection',''),validate='one_to_one')
    batch.to_csv(DEST/BATCH/'outcomes.csv',index=False)
    merged[merged.test_added_content_verified.isna()].to_csv(DEST/'current_unknown_queue.csv',index=False)
    y=pd.to_numeric(merged.test_added_content_verified,errors='coerce');b=pd.to_numeric(batch.test_added_content_verified,errors='coerce')
    stats={'main':{'positive':int(y.eq(1).sum()),'negative':int(y.eq(0).sum()),'unknown':int(y.isna().sum())},'batch':{'selected':len(sample),'positive':int(b.eq(1).sum()),'negative':int(b.eq(0).sum()),'unknown':int(b.isna().sum()),'checkpointed':len(done),'checkpoint_records':len(done),'fully_resolved':int(b.notna().sum()),'checkpointed_is_not_completed':True},'batch_file_methods':pd.concat(audits).classification_method.value_counts().to_dict() if audits and 'classification_method' in pd.concat(audits) else {},'batch_files_inspected':int(done.n_files_inspected.sum()) if 'n_files_inspected' in done else 0,'batch_files_avoided':int(done.files_avoided_early_exit.sum()) if 'files_avoided_early_exit' in done else 0}
    stats['batch'].update(checkpointed=checkpoint_count,checkpoint_records=checkpoint_count)
    if not delta.empty:
        stats['cohort_overlay']=cohort_overlay.VERSION
    write_json(DEST/'progress.json',stats);return stats

def main():
    global BATCH
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--deterministic-only',action='store_true',help='Never dispatch paid model calls; cached validated decisions remain usable');p.add_argument('--fetch-github',action='store_true');p.add_argument('--github-limit',type=int,default=1500);p.add_argument('--retry-unknown',action='store_true');p.add_argument('--batch-number',type=int,default=1);p.add_argument('--prioritize-low-cost',action='store_true')
    add_model_limits(p)
    p.add_argument('--rearm-model-quality', action='store_true',
                   help='Start one separate quality window for this prompt and validator; never resets an existing trial')
    p.add_argument('--rearm-model-transport', action='store_true',
                   help='Probe with corrected credentials using up to two new attempts; retain cached failures')
    p.add_argument('--evidence-v5', action='store_true',
                   help='Use the revised evidence request after the three-case trial passes')
    args=p.parse_args()
    validate_model_limits(p,args)
    delta=runner_delta()
    pending_trial=cohort_overlay.reference_trial_required(DEST)
    if pending_trial and delta.empty:
        p.error('Admit the verified v1 delta with cohort_overlay.py before scheduling any work.')
    if pending_trial and (args.evidence_v5 or args.rearm_model_quality
            or args.rearm_model_transport or (args.live and not args.deterministic_only
            and args.max_new_model_calls>0)):
        p.error('Paid cohort dispatch is locked. Use independent_review.py for the controlled trial.')
    if args.evidence_v5:
        if (not args.live or args.deterministic_only or args.fetch_github
                or args.rearm_model_quality or args.rearm_model_transport):
            p.error('--evidence-v5 requires a live run from cached GitHub evidence without rearm flags')
        from evidence_trial import admit_trial_cache
        admit_trial_cache(DEST,engine.ScalingBudget().state['attempts'])
    if args.rearm_model_quality and (not args.live or args.deterministic_only):
        p.error('--rearm-model-quality requires a live hybrid run')
    if args.rearm_model_transport:
        if not args.live or args.deterministic_only:
            p.error('--rearm-model-transport requires a live hybrid run')
        if not 1 <= args.max_new_model_calls <= 2:
            p.error('--rearm-model-transport requires --max-new-model-calls 1 or 2')
    if args.batch_number<1:raise ValueError('Batch number must be positive')
    BATCH=f'batch_{args.batch_number:04d}'
    DEST.mkdir(exist_ok=True);protect_prior();entry=freeze_inputs();queue,sample=make_queue(entry)
    protect_selection()
    B=DEST/BATCH
    for part in ['checkpoints','results','audits']: (B/part).mkdir(exist_ok=True)
    rawgroups=groups();write_json(DEST/'resource_estimate.json',estimate(sample,rawgroups,args))
    if args.live and not args.deterministic_only and not os.environ.get('XAI_API_KEY','').strip():print('Blocked: missing XAI_API_KEY; no network/model requests. Offline preparation complete.');return
    engine.DEST=B
    budget=engine.ScalingBudget(max_spend=args.max_grok_spend)
    ledger=budget.state['attempts']
    budget.max_requests=min(args.max_grok_requests,len(ledger)+args.max_new_model_calls)
    live_model=args.live and not args.deterministic_only
    circuit=(evidence_v5_circuit_path(DEST) if args.evidence_v5 else
             quality_circuit_path(DEST, args.rearm_model_quality)) if live_model else None
    resolver=engine.Resolver(dry_run=not live_model,budget=budget,circuit_path=circuit,
                             fallback_on_quality=True,rearm_transport=args.rearm_model_transport,
                             defer_request_limit=True,evidence_v5=args.evidence_v5)
    from progress_audit import audit_pending
    previous=pd.read_csv(B/'outcomes.csv') if (B/'outcomes.csv').exists() else pd.DataFrame(columns=KEY+['test_added_content_verified'])
    previous=cohort_overlay.apply_delta(previous,delta)
    recovered=set(delta[KEY].itertuples(index=False,name=None))
    states=audit_pending(sample,previous,rawgroups,engine.Resolver(dry_run=True))
    states.to_csv(B/'progress_states.csv',index=False)
    actionable=set(map(tuple,states.loc[states.actionable_now,KEY].to_numpy()))
    state_by_key={tuple(row[k] for k in KEY):row['verification_state'] for row in states.to_dict('records')}
    mixed_blockers=set()
    if args.evidence_v5:
        for state in states.to_dict('records'):
            if state['verification_state']=='waiting_grok_classification' and any(
                    not isinstance(item,dict) or item.get('model_status') not in {'dry_run','missing_XAI_API_KEY'}
                    for item in json.loads(state['details'])):
                mixed_blockers.add(tuple(state[k] for k in KEY))
    accounting={'attempted_prs':0,'resolved_prs_skipped':0,'nonactionable_skipped':0,'actionable_skipped_by_reason':{}}
    work_sample=prioritize_remaining(sample,states) if args.prioritize_low_cost else sample
    if args.prioritize_low_cost:
        plans=B/'execution_plans';plans.mkdir(exist_ok=True)
        work_sample[KEY+['execution_rank']].to_csv(plans/(str(time.time_ns())+'.csv'),index=False)
    stop=None
    updated=0
    try:
        for row in work_sample.to_dict('records'):
            ident=stable_hash(f'{row["repo_name"]}|{row["pr_number"]}')[:24];path=B/'results'/(ident+'.csv')
            key=tuple(row[k] for k in KEY)
            if key in recovered:
                accounting['resolved_prs_skipped']+=1
                continue
            if not needs_processing(path,args.live or args.deterministic_only,args.retry_unknown):
                if state_by_key.get(key) in {'confirmed_positive','exhaustively_verified_negative'}:accounting['resolved_prs_skipped']+=1
                continue
            if (args.live or args.deterministic_only) and not args.retry_unknown and key not in actionable:
                accounting['nonactionable_skipped']+=1;continue
            resources=resource_status(args,resolver)
            blocked=resource_block_reason(state_by_key.get(key),resources['github_remaining'],
                                          args.fetch_github,resources['grok_requests_enabled'])
            if args.evidence_v5 and key in mixed_blockers:
                blocked='independent_evidence_blocker'
            if blocked:
                if blocked == 'model_requests_disabled_or_unavailable':
                    if resolver.transport_blocked:
                        blocked = 'model_transport_blocked_invalid_argument'
                    elif live_model and resources['grok_current_run_remaining']==0:
                        blocked = 'grok_request_limit_reached'
                counts=accounting['actionable_skipped_by_reason'];counts[blocked]=counts.get(blocked,0)+1
                continue
            accounting['attempted_prs']+=1
            before_pr_calls=len(resolver.budget.state['attempts'])
            pr_resolver=resolver
            if args.evidence_v5 and state_by_key.get(key)=='cache_ready_for_replay':
                pr_resolver=engine.Resolver(dry_run=True)
            d,a,q=engine.run_rows(pd.DataFrame([row]),pr_resolver,args.fetch_github,args.github_limit,rawgroups,allow_missing_resources=True)
            d['processing_mode']='deterministic_only' if args.deterministic_only else 'transport_fallback' if resolver.transport_blocked else 'quality_fallback' if resolver.model_disabled else 'hybrid'
            d['new_model_requests']=len(resolver.budget.state['attempts'])-before_pr_calls
            d['processed_without_new_grok']=d['new_model_requests'].eq(0)
            d.to_csv(path,index=False);a.to_csv(B/'audits'/(ident+'.csv'),index=False)
            # Each PR has durable results; aggregate periodically to avoid O(n²)
            # file reads. The finally block always publishes a stopped run.
            updated+=1
            if updated%20==0:publish(entry,sample)
    except GitHubLowQuota:
        quota=json.loads((B/'github_quota_observation.json').read_bytes())
        stop={'status':'paused','reason':'github_low_quota',
              'remaining':quota['remaining'],'limit':quota['limit'],'reset_epoch':quota['reset_epoch']}
        write_json(DEST/'stop_status.json',stop)
    except Exception as exc:
        stop={'status':'stopped','exception_type':type(exc).__name__,'reason':str(exc) if isinstance(exc,RuntimeError) else 'unexpected_error_inspect_locally'}
        write_json(DEST/'stop_status.json',stop)
        raise
    finally:
        stats=publish(entry,sample)
        final_states=audit_pending(sample,pd.read_csv(B/'outcomes.csv'),rawgroups,engine.Resolver(dry_run=True))
        final_states.to_csv(B/'progress_states.csv',index=False)
        stats['batch']['pending_actionable']=int(final_states.actionable_now.sum())
        stats['batch']['blocked_unknown']=int((final_states.resumable & ~final_states.actionable_now).sum())
        stats['model_quality_fallback']=resolver.model_disabled
        stats['deterministic_only']=args.deterministic_only
        stats['verification_states']=final_states.verification_state.value_counts().to_dict()
        stats['resources']=resource_status(args,resolver)
        stats['execution']=accounting
        stats['execution']['stop_reasons']=list(accounting['actionable_skipped_by_reason'])
        if live_model and stats['resources']['grok_current_run_remaining']==0:
            if 'grok_request_limit_reached' not in stats['execution']['stop_reasons']:
                stats['execution']['stop_reasons'].append('grok_request_limit_reached')
        stats['execution']['resolved_delta']=stats['batch']['fully_resolved']-int(previous.test_added_content_verified.notna().sum())
        if stop and stop['status']=='paused':
            stats['execution']['stop_reasons'].append(stop['reason'])
            stats['execution']['completion_status']='github_quota_paused'
            stats['execution']['github_quota_pause']=stop
        else:
            stats['execution']['completion_status']='error' if stop else 'resource_blocked' if not accounting['attempted_prs'] and accounting['actionable_skipped_by_reason'] else 'bounded_pass_finished'
        write_json(DEST/'progress.json',stats)
        write_json(DEST/'api_usage.json',grok.usage_report(resolver.budget));protect_prior();print(json.dumps(stats,indent=2))
if __name__=='__main__':
    with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):main()
