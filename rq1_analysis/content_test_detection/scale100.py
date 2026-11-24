from github_http import GitHubLowQuota,read_count
"""Separate reconciliation and resumable 100-PR experiment; no regression execution."""
import argparse,csv,json,math,os,re,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import requests
import portalocker
import grok
from common import HERE,BASE,HIST,OUT,CACHE,KEY,stable_hash,sha256,write_json,protect_prior
from detector import eligible,language
from pipeline import hybrid,search_pr
from storage import Store,metadata_request
from fetch_github import normalize
from urllib.parse import quote

DEST=OUT/'scale100'

class Resolver(grok.GrokResolver):
    def __init__(self,*args,**kwargs):
        self.fallback_on_quality=kwargs.pop('fallback_on_quality',False)
        self.model_disabled=False
        self.fallback_reason=None
        self.circuit_path=kwargs.pop('circuit_path',None)
        rearm_transport=kwargs.pop('rearm_transport',False)
        self.defer_request_limit=kwargs.pop('defer_request_limit',False)
        super().__init__(*args,**kwargs)
        latest = self.budget.state['attempts'][-1:]
        failed_probe = bool(latest and latest[0].get('transport_rearm_probe')
                            and latest[0].get('usage') is None)
        blocked = not self.dry_run and (failed_probe or self.repeated_invalid_arguments())
        self.transport_rearmed = blocked and rearm_transport
        self.transport_blocked = blocked and not self.transport_rearmed
        if self.transport_rearmed:
            # Also enforce the trial cap here for direct callers.
            self.budget.max_requests = min(self.budget.max_requests, 1000,
                                           len(self.budget.state['attempts']) + 2)
            self.budget.transport_rearm_probe = True
        self.consecutive_failures=0
        self.file_specific_failures={}
        records=json.loads(self.circuit_path.read_text()) if self.circuit_path and self.circuit_path.exists() else []
        # Schema/protocol monitoring must not inherit corrected historical
        # decisions or a different prompt's failures. Original audit stays intact.
        unique={row.get('cache_key'):row for row in records if isinstance(row,dict) and row.get('origin')=='live' and row.get('prompt_version')==self.prompt_version and row.get('cache_key')}
        self.recent_results=list(unique.values())[-10:]
        for row in self.recent_results:
            recovered=CACHE/'offline_revalidated'/(row['cache_key']+'.json')
            source=OUT/'content'/(str(row.get('hash'))+'.txt')
            if row.get('failed') and recovered.exists() and source.exists():
                record=json.loads(recovered.read_text());raw=source.read_bytes()
                assert sha256(raw)==row['hash'] and record['content_sha256']==row['hash']
                grok.validate_cached_classification(record,raw.decode('utf-8-sig'))
                row.update(failed=False,original_failed=True,revalidated_offline=True,revalidation_reference=str(recovered))
        if self.fallback_on_quality and self.quality_tripped():self.disable_model()

    def repeated_invalid_arguments(self):
        """Two consecutive rejections of the current request format block dispatch."""
        attempts = self.budget.state['attempts'][-2:]
        if len({row['task'] for row in attempts}) != 2:
            return False
        for row in attempts:
            if row.get('transport_status') != 'INVALID_ARGUMENT':
                return False
            key = row['task']
            if not re.fullmatch('[0-9a-f]{64}', key):
                return False
            path = CACHE / 'grok' / f'{key}.json'
            if not path.is_file():
                return False
            record = json.loads(path.read_text())
            if (record.get('status') != 'provider_or_validation_failure'
                    or record.get('model') != grok.MODEL
                    or record.get('reasoning_effort') != grok.REASONING
                    or record.get('prompt_version') not in {grok.PROMPT_VERSION,grok.EVIDENCE_V5}
                    or grok.cache_key(record.get('content_sha256'),record['prompt_version']) != key):
                return False
            diagnostic = record.get('diagnostic', {})
            if (diagnostic.get('stage') != 'transport'
                    or diagnostic.get('transport_status') != 'INVALID_ARGUMENT'
                    or diagnostic.get('prompt_sha256') != sha256((grok.SYSTEM_V5 if record['prompt_version']==grok.EVIDENCE_V5 else grok.SYSTEM).encode())):
                return False
        return True

    def quality_tripped(self):
        failures=[r['repo'] for r in self.recent_results if r.get('failed')]
        if self.prompt_version==grok.EVIDENCE_V5 and len(self.recent_results)<10:
            # A three-case gate is a smoke test. Stop an early regression
            # across repositories without waiting for a full ten decisions.
            return len(set(failures))>=2
        return len(self.recent_results)==10 and len(failures)>=5 and len(set(failures))>=3
    def disable_model(self):
        self.model_disabled=True;self.fallback_reason='systematic_model_validation_failures'
        if self.circuit_path:write_json(self.circuit_path.with_suffix('.fallback.json'),{'new_model_requests_disabled':True,'reason':self.fallback_reason,'window':self.recent_results,'scope':'current invocation; cached valid responses remain usable'})
    def resolve(self,text,path,lang,raw_hash,strong=None):
        key=grok.cache_key(raw_hash,self.prompt_version)
        for root in [CACHE/'offline_revalidated',CACHE/'repair_smoke/grok',CACHE/'grok']:
          for p in sorted(root.glob('*.json')):
            r=json.loads(p.read_text())
            if r.get('content_sha256')!=raw_hash:continue
            if r.get('status')!='validated':continue
            assert r['content_sha256']==raw_hash and r['model']==grok.MODEL and r['reasoning_effort']==grok.REASONING
            grok.validate_cached_classification(r,text)
            return {**r,'cache_hit':True,'classification_cache_reference':p.relative_to(BASE.parent).as_posix()}
        # Preserve legacy failed inputs as unknown; strategy changes never force
        # automatic paid resubmission of previously rejected content.
        for root in [CACHE/'repair_smoke/grok',CACHE/'grok']:
            for p in root.glob('*.json'):
                old=json.loads(p.read_text())
                if old.get('content_sha256')==raw_hash and old.get('status')=='provider_or_validation_failure':return {**old,'cache_hit':True}
        group=(getattr(self,'current_repo','unknown'),getattr(self,'current_pr',None))
        if self.transport_blocked:
            return {'classification':'uncertain','has_executable_tests':None,'needs_review':True,
                    'evidence':[],'method':'Grok','status':'model_transport_blocked_invalid_argument',
                    'reason':'Repeated provider rejection or unconfirmed transport rearm probe'}
        if self.model_disabled:
            return {'classification':'uncertain','has_executable_tests':None,'needs_review':True,'evidence':[],'method':'Grok','status':'model_quality_fallback','reason':'New requests disabled by quality circuit; source remains unresolved'}
        if self.file_specific_failures.get(group,0)>=3:
            return {'classification':'uncertain','has_executable_tests':None,'needs_review':True,'evidence':[],'status':'per_pr_model_deferred','method':'Grok','reason':'Three rejected responses in this PR; continue static/cache analysis without further paid calls'}
        r=super().resolve(text,path,lang,raw_hash,strong)
        if r.get('status') == 'request_limit' and self.defer_request_limit:
            # No request was dispatched. Leave this file unknown and let the PR
            # finish using cached evidence or deterministic checks.
            return r
        if r.get('status') in {'request_limit','spending_limit','scaling_preflight_not_satisfied','invalid_cached_prediction'}:
            raise RuntimeError('stopped_'+r['status'])
        if r.get('status')=='provider_or_validation_failure':
            diagnostic=r.get('diagnostic',{})
            recoverable=diagnostic.get('stage') in {'schema_or_evidence','original_source_evidence','finish_reason'} and r.get('error_type') in {'ValueError','ValidationError'}
            # Old failed entries lacking diagnostics remain unresolved and cached.
            if not recoverable and not r.get('cache_hit'):
                transport_status = diagnostic.get('transport_status')
                if diagnostic.get('stage') == 'transport' and transport_status:
                    raise RuntimeError(f'model_transport_failure_{transport_status}; inspect cached diagnostic')
                raise RuntimeError('unexpected_model_failure; inspect cached diagnostic')
            if not r.get('cache_hit'):
                self.file_specific_failures[group]=self.file_specific_failures.get(group,0)+1
        decision_key=r.get('cache_key') or key
        if not r.get('cache_hit') and r.get('status') in {'validated','provider_or_validation_failure'} and decision_key not in {row.get('cache_key') for row in self.recent_results if isinstance(row,dict)}:
            self.recent_results.append({'failed':r['status']!='validated','repo':group[0],'pr':group[1],'path':path,'hash':raw_hash,'cache_key':decision_key,'status':r['status'],'finish':r.get('finish_reason',r.get('diagnostic',{}).get('finish_reason')),'prompt_version':r.get('prompt_version',self.prompt_version),'validator_version':grok.VALIDATOR_VERSION,'origin':'live','diagnostic':r.get('diagnostic')})
        self.recent_results=self.recent_results[-10:]
        if self.circuit_path:write_json(self.circuit_path,self.recent_results)
        # Independent-repository denominator prevents treating three correlated
        # files from one PR as a provider-wide incident. Stop on >=50% rejection
        # in ten new decisions, spanning >=3 affected repositories.
        failures=[row['repo'] if isinstance(row,dict) else row[1] for row in self.recent_results if (row['failed'] if isinstance(row,dict) else row[0])]
        if self.quality_tripped():
            if self.fallback_on_quality:self.disable_model()
            else:raise RuntimeError('systematic_model_validation_failures; >=50% in ten decisions across three repositories')
        if r.get('status')=='validated' and self.cache_dir!=grok.CACHE/'grok':
            r['classification_cache_reference']=(self.cache_dir/(decision_key+'.json')).relative_to(BASE.parent).as_posix()
        return r

class ScalingBudget(grok.Budget):
    max_authorized_spend = 7.0

    @staticmethod
    def accounted_attempt(row):
        amount = row.get('charged_or_reserved_usd')
        if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
            return False
        if 'reported_cost_usd' in row:
            reported = row['reported_cost_usd']
            return type(reported) in (int, float) and reported == amount
        # A terminal failure may have no cost receipt. Carry the entire
        # positive reservation forward; missing or altered accounting fails closed.
        return (row.get('status') == 'failed_or_invalid_reserved'
                and amount > 0 and row.get('reserved_usd') == amount)

    def reserve(self,bound,task):
        # Require validated smoke results and accountable charges/reservations.
        good=set()
        for root in [CACHE/'grok',CACHE/'repair_smoke/grok']:
            for p in root.glob('*.json'):
                r=json.loads(p.read_text())
                if r.get('status')=='validated':good.add(r['content_sha256'])
        rows=self.state['attempts']
        if len(good)<9 or not all(self.accounted_attempt(r) for r in rows):raise RuntimeError('scaling_preflight_not_satisfied')
        if len(rows)>=self.max_requests:raise RuntimeError('request_limit')
        if sum(r['charged_or_reserved_usd'] for r in rows)+bound>self.max_spend:raise RuntimeError('spending_limit')
        rows.append({'task':task,'reserved_usd':bound,'charged_or_reserved_usd':bound,'status':'reserved','key_present_at_dispatch':bool(os.environ.get('XAI_API_KEY','').strip()),'at':datetime.now(timezone.utc).isoformat(),'policy':'scale100_scoped_preflight'})
        if getattr(self, 'transport_rearm_probe', False):
            rows[-1]['transport_rearm_probe'] = True
        write_json(self.path,self.state);return len(rows)-1


def run_rows(frame,resolver,fetch=False,github_limit=500,groups=None,allow_missing_resources=False):
    if groups is None:
        raw=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=KEY+['file_path','change_status'])
        groups={k:g for k,g in raw.groupby(KEY)}
    results=[];audits=[];frontier=[]
    used_start=read_count(CACHE)
    session=requests.Session();session.headers['Accept']='application/vnd.github+json'
    if os.environ.get('GITHUB_TOKEN'):session.headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    def acquire(req):
        if read_count(CACHE)>=github_limit:return False
        a=req['args'];kind=req['kind']
        url=f"https://api.github.com/repos/{a['repository_full_name']}/pulls/{a['pr_number']}" if kind=='metadata' else f"https://api.github.com/repos/{a['repository_full_name']}/contents/{quote(a['path'],safe='/')}?ref={a['ref']}" if kind=='content' else f"https://api.github.com/repos/{a['repository_full_name']}/git/blobs/{a['sha']}" if kind=='blob' else a['url']
        from github_http import get_with_retry
        resp=get_with_retry(session,url,req,CACHE,github_limit)
        write_json(DEST/'github_quota_observation.json',{'observed_at':datetime.now(timezone.utc).isoformat(),'remaining':resp.headers.get('X-RateLimit-Remaining'),'limit':resp.headers.get('X-RateLimit-Limit'),'reset_epoch':resp.headers.get('X-RateLimit-Reset'),'http_status':resp.status_code,'request':req,'content_type':resp.headers.get('Content-Type')})
        if allow_missing_resources and resp.status_code in {404,410}:
            write_json(CACHE/'github'/(req['id']+'.json'),{'request':req,'ok':False,'error':'http_'+str(resp.status_code),'retrieved_at':datetime.now(timezone.utc).isoformat(),'transport':'bounded GET'},immutable=True)
            return True
        if not resp.ok:raise RuntimeError('github_http_'+str(resp.status_code)+'; stopped without negative assignment')
        body=resp.json()
        if kind in {'content','blob'}:
            directory=DEST/'retrieval_diagnostics';directory.mkdir(exist_ok=True)
            write_json(directory/(req['id']+'.json'),{'request':req,'http_status':resp.status_code,'content_type':resp.headers.get('Content-Type'),'response_shape':type(body).__name__,'keys':sorted(body) if isinstance(body,dict) else None,'metadata':{k:body.get(k) for k in ['type','encoding','size','sha'] if k in body} if isinstance(body,dict) else {}})
        write_json(CACHE/'github'/(req['id']+'.json'),{'request':req,'ok':True,'data':normalize(kind,body),'retrieved_at':datetime.now(timezone.utc).isoformat(),'transport':'scale100 GET'},immutable=True)
        if int(resp.headers.get('X-RateLimit-Remaining','100'))<=10:raise GitHubLowQuota()
        time.sleep(.5);return True
    for row in frame.to_dict('records'):
        repo,num=row['repo_name'],int(row['pr_number']);key=(repo,num)
        while True:
            store=Store();meta=store.data(metadata_request(repo,num));files,complete,pending,reason=store.files(repo,num)
            audit=[]
            if meta is None or files is None:
                outcome={'test_added_content_verified':None,'unknown_reason':reason,'n_files_inspected':0,'n_eligible_added_files':sum(r.change_status=='added' and eligible(r.file_path) for r in groups[key].itertuples())}
            else:
                aligned={(r.file_path,r.change_status) for r in groups[key].itertuples()}=={(f['filename'],f['status']) for f in files}
                def get(f):
                    result=store.content(repo,meta['head_sha'],f['filename'],f.get('sha'))
                    if result[1].get('integrity_error'):
                        directory=DEST/'integrity_failures';directory.mkdir(exist_ok=True)
                        write_json(directory/(stable_hash(f'{repo}|{num}|{f["filename"]}')[:24]+'.json'),{'repo_name':repo,'pr_number':num,'file_path':f['filename'],'pinned_commit_sha':meta['head_sha'],'expected_pr_file_sha':f.get('sha'),'diagnostic':result[1]})
                        raise RuntimeError('source_hash_mismatch; verification halted')
                    return result
                def classify(text,f,prov):
                    resolver.current_repo=repo
                    resolver.current_pr=num
                    v,ai=hybrid(text,f['filename'],prov['content_sha256'],resolver)
                    if ai and ai.get('classification_cache_reference'):v['evidence_reference']=ai['classification_cache_reference']
                    if ai and ai.get('status')=='provider_or_validation_failure':
                        failure={'repo_name':repo,'pr_number':num,'file_path':f['filename'],'commit_sha':meta['head_sha'],'content_sha256':prov['content_sha256'],'status':ai['status'],'diagnostic':ai.get('diagnostic'),'cache_key':ai.get('cache_key'),'cache_hit':ai.get('cache_hit',False),'outcome':'unresolved; continue other added files'}
                        directory=DEST/'file_failures';directory.mkdir(exist_ok=True)
                        write_json(directory/(stable_hash(f'{repo}|{num}|{f["filename"]}')[:24]+'.json'),failure)
                    return v
                outcome,audit,requests_pending=search_pr(files,get,classify,complete,'net_diff_changed_from_frozen_study' if complete and not aligned else None)
                if not pending:pending=requests_pending
                if outcome['test_added_content_verified']==1:pending=[]
            if fetch and pending and acquire(pending[0]):continue
            frontier.extend(pending[:1]);break
        base={k:row.get(k) for k in KEY+['tool','has_acceptance_criteria','has_edge_cases','test_added','repo_language']}
        results.append({**base,**outcome,'pinned_commit_sha':meta.get('head_sha') if meta else None})
        audits.extend({**base,**r} for r in audit)
        write_json(DEST/'checkpoints'/(stable_hash(f'{repo}|{num}')[:24]+'.json'),results[-1])
    return pd.DataFrame(results),pd.DataFrame(audits),frontier


def select100(reconciled):
    path=DEST/'sample100.csv'
    if path.exists():return pd.read_csv(path)
    main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    unknown=set(map(tuple,reconciled.loc[reconciled.test_added_content_verified.isna(),KEY].to_numpy()))
    pool=main[[tuple(k) in unknown for k in main[KEY].to_numpy()]].copy()
    pool=pool[pool.tool.isin(['openspec','speckit'])].copy()
    pool['selection_hash']=[stable_hash(f'scale100-v1|{r}|{n}') for r,n in pool[KEY].to_numpy()]
    pool['stratum']=pool.tool.astype(str)+'|'+pool.has_acceptance_criteria.astype(str)+'|'+pool.has_edge_cases.astype(str)
    records=pool.sort_values('selection_hash').to_dict('records');chosen=[];repos={};strata={}
    while len(chosen)<100 and records:
        r=min(records,key=lambda r:(strata.get(r['stratum'],0),repos.get(r['repo_name'],0),r['selection_hash']))
        records.remove(r);chosen.append(r);repos[r['repo_name']]=repos.get(r['repo_name'],0)+1;strata[r['stratum']]=strata.get(r['stratum'],0)+1
    d=pd.DataFrame(chosen);d.to_csv(path,index=False);return d


def summary(d,audit):
    y=pd.to_numeric(d.test_added_content_verified,errors='coerce');known=y.notna()
    return {'n_prs':len(d),'positive':int(y.eq(1).sum()),'negative':int(y.eq(0).sum()),'unknown':int(y.isna().sum()),'files_inspected':int(d.n_files_inspected.sum()),'files_avoided_early_exit':int(d.get('files_avoided_early_exit',pd.Series(dtype=float)).sum()),'file_method_counts':audit.get('classification_method',pd.Series(dtype=str)).value_counts().to_dict(),'path_label_changes':int(d.loc[known,'test_added'].astype(int).ne(y[known].astype(int)).sum())}


def reconcile_registry():
    sources={}
    for root in [HIST/'outputs/content',OUT/'content']:
        for p in root.rglob('*'):
            if p.is_file():
                raw=p.read_bytes()
                try:sources[sha256(raw)]=raw.decode('utf-8-sig')
                except UnicodeDecodeError:pass
    merged={}
    for root in [CACHE/'grok',CACHE/'repair_smoke/grok',CACHE/'offline_revalidated']:
        for p in root.glob('*.json'):
            r=json.loads(p.read_text());h=r['content_sha256']
            if r.get('status')=='validated':
                grok.validate_cached_classification(r,sources[h])
            if h not in merged or r.get('status')=='validated':merged[h]={**r,'classification_cache_reference':p.relative_to(BASE.parent).as_posix()}
    write_json(DEST/'reconciled_classification_registry.json',list(merged.values()))
    return merged


def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--fetch-github',action='store_true');p.add_argument('--max-grok-requests',type=int,default=100);p.add_argument('--github-limit',type=int,default=500);args=p.parse_args()
    from cohort_overlay import reference_trial_required
    if args.live and reference_trial_required(OUT/'full_cohort'):
        p.error('The 100-PR paid runner is closed. See independent_review.py.')
    DEST.mkdir(exist_ok=True);(DEST/'checkpoints').mkdir(exist_ok=True);protect_prior()
    if args.live and not os.environ.get('XAI_API_KEY','').strip():print('Blocked: missing XAI_API_KEY; no new requests. Run without --live for offline reconciliation.');return
    reconcile_registry()
    resolver=Resolver(dry_run=not args.live,budget=ScalingBudget(max_requests=args.max_grok_requests,max_spend=3),circuit_path=DEST/'circuit_state_source-reference-v3.json' if args.live else None)
    mainframe=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    # Reconciliation is always offline, using all validated cached responses.
    offline=Resolver(dry_run=True)
    rec,ra,_=run_rows(mainframe,offline)
    rec.to_csv(DEST/'reconciled_main_outcomes.csv',index=False);ra.to_csv(DEST/'reconciled_inspection_audit.csv',index=False)
    write_json(DEST/'reconciliation_summary.json',summary(rec,ra))
    sample=select100(rec)
    source=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=KEY+['file_path','change_status'])
    source=source.merge(sample[KEY],on=KEY);n=int(sum(r.change_status=='added' and eligible(r.file_path) for r in source.itertuples()))
    estimate={'selected_prs':len(sample),'repositories':sample.repo_name.nunique(),'strata':sample.stratum.value_counts().to_dict(),'worst_case_metadata_requests':100,'worst_case_file_pages':int(((sample.n_files+99)//100).sum()),'eligible_added_source_files_upper_bound':n,'grok_calls_range':[0,n],'configured_cumulative_grok_attempt_ceiling':args.max_grok_requests,'configured_cumulative_spend_usd':3,'illustrative_cost_per_10k_input_1200_output_call_usd':.0155,'new_github_reads_available_under_cap':max(0,args.github_limit-read_count(CACHE)),'note':'Bounds before cache reuse and early stopping; not a population ambiguity forecast.'}
    write_json(DEST/'acquisition_estimate.json',estimate)
    before=len(resolver.budget.state['attempts'])
    try:d,a,q=run_rows(sample,resolver,args.fetch_github,args.github_limit)
    except Exception as e:
        write_json(DEST/'stop_status.json',{'status':'stopped','exception_type':type(e).__name__,'reason':str(e) if isinstance(e,RuntimeError) else 'unexpected_error_inspect_locally','checkpoints_preserved':True});raise
    d.to_csv(DEST/'pr_outcomes.csv',index=False);a.to_csv(DEST/'inspection_audit.csv',index=False);write_json(DEST/'github_frontier.json',q)
    write_json(DEST/'summary.json',{**summary(d,a),'new_api_attempts':len(resolver.budget.state['attempts'])-before,'pending_github_frontiers':len(q)})
    write_json(DEST/'api_usage.json',grok.usage_report(resolver.budget));protect_prior()
    print(json.dumps({'reconciled':summary(rec,ra),'experiment':summary(d,a),'cumulative_cost':sum(r.get('reported_cost_usd',0) for r in resolver.budget.state['attempts'])},indent=2))
if __name__=='__main__':
    with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):main()
