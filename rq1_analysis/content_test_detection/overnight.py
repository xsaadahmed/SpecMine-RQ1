from github_http import read_count
"""Bounded unattended passes using the existing runner; never resets API ledgers."""
import argparse,csv,json,os,subprocess,sys,time
from collections import deque
from datetime import datetime,timezone
import requests,portalocker
import full_cohort as core
from common import HERE,OUT,CACHE,write_json,protect_prior

ROOT=OUT/'full_cohort'

def ledger():return json.loads((OUT/'api_ledger.json').read_text())['attempts']
def money(rows):return sum(r['charged_or_reserved_usd'] for r in rows)
def mode_allowed(rows, max_requests=100, max_spend=3):
    return bool(os.environ.get('XAI_API_KEY','').strip()) and len(rows)<max_requests and money(rows)<max_spend


def model_batch_priority(batch):
    """Rank complete-evidence model candidates ahead of mixed blockers."""
    path=ROOT/f'batch_{batch:04d}/progress_states.csv'
    if not path.is_file():
        return (2,0,0,batch)
    counts=[]
    with path.open(encoding='utf-8-sig',newline='') as source:
        for row in csv.DictReader(source):
            if row['verification_state']!='waiting_grok_classification':
                continue
            details=json.loads(row['details'])
            if details and all(isinstance(item,dict) and item.get('model_status') in
                               {'dry_run','missing_XAI_API_KEY'} for item in details):
                counts.append(len(details))
    return (0,min(counts),-counts.count(min(counts)),batch) if counts else (1,0,0,batch)


def saved_quality_block(evidence_v5=False):
    circuit=core.evidence_v5_circuit_path(ROOT) if evidence_v5 else core.quality_circuit_path(ROOT)
    if not circuit.exists():
        return False
    # Dry resolver revalidates any recovered responses without resetting the window.
    return core.engine.Resolver(dry_run=True,circuit_path=circuit,evidence_v5=evidence_v5).quality_tripped()

def quota(session):
    try:
        response=session.get('https://api.github.com/rate_limit',timeout=30)
    except requests.RequestException:
        return {'allowed':False,'reason':'github_quota_transport_error'}
    if response.status_code!=200:return {'allowed':False,'reason':'github_quota_http_'+str(response.status_code)}
    try:
        value=response.json()['resources']['core']
        return {'allowed':int(value['remaining'])>20,'remaining':int(value['remaining']),'limit':int(value['limit']),'reset_epoch':int(value['reset']),'reason':'ready' if int(value['remaining'])>20 else 'github_quota_low'}
    except (KeyError,TypeError,ValueError):return {'allowed':False,'reason':'invalid_quota_response'}

def child_command(batch,github_limit,hybrid,max_requests=100,max_new_calls=10,max_spend=3,
                  fetch=True, prioritize=True):
    command=[sys.executable,'-B',str(HERE/'full_cohort.py'),'--batch-number',str(batch),'--github-limit',str(github_limit),'--max-grok-requests',str(max_requests),'--max-new-model-calls',str(max_new_calls),'--max-grok-spend',str(max_spend)]
    if fetch:command.append('--fetch-github')
    if prioritize:command.append('--prioritize-low-cost')
    command.append('--live' if hybrid else '--deterministic-only');return command

def wait_for_quota(status,state,directory,enabled):
    if not enabled or status.get('remaining',21)>20 or not status.get('reset_epoch'):return False
    seconds=max(1,status['reset_epoch']-int(time.time())+5)
    if seconds+state.get('waited_seconds',0)>3660:return False
    state['waited_seconds']=state.get('waited_seconds',0)+seconds
    write_json(directory/'waiting.json',{'reason':'authenticated_primary_quota_reset','sleep_seconds':seconds,'reset_epoch':status['reset_epoch']})
    # Short chunks also permit normal Ctrl-C interruption and finally reporting.
    while seconds>0:
        step=min(30,seconds);time.sleep(step);seconds-=step
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--github-limit',type=int,default=7500);p.add_argument('--max-passes',type=int,default=100);p.add_argument('--wait-for-reset',action='store_true')
    p.add_argument('--prioritize-low-cost', action=argparse.BooleanOptionalAction, default=True)
    p.add_argument('--evidence-v5', action='store_true', help='Use the revised strategy after its controlled trial passes')
    core.add_model_limits(p)
    args=p.parse_args()
    core.validate_model_limits(p,args)
    if core.cohort_overlay.reference_trial_required(ROOT) and args.evidence_v5:
        p.error('Evidence v5 is retired. See independent_review.py for the controlled trial.')
    if args.evidence_v5:
        if not args.live:p.error('--evidence-v5 requires --live')
        from evidence_trial import admit_trial_cache
        with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):
            admit_trial_cache(ROOT,ledger())
    if not 1<=args.max_passes<=200:p.error('--max-passes must be 1..200')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+str(time.time_ns())
    D=ROOT/'overnight_runs'/stamp;D.mkdir(parents=True)
    before=json.loads((ROOT/'progress.json').read_text())['main'];events=[];stop='pass_limit'
    state={'initial_main':before,'events':events,'limits':{'github_cumulative':args.github_limit,'grok_lifetime_attempts':args.max_grok_requests,'spend_usd':args.max_grok_spend,'new_grok_attempts_per_child':args.max_new_model_calls,'passes':args.max_passes},'quota_checks':0}
    write_json(D/'state.json',state)
    if not args.live:
        print('Prepared runner; no network or model calls. Use --live in the authenticated terminal.');return
    if not os.environ.get('GITHUB_TOKEN','').strip():
        state['stop_reason']='missing_GITHUB_TOKEN';write_json(D/'state.json',state);print('Stopped: authenticated GitHub token unavailable.');return
    session=requests.Session();session.headers.update({'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'CS520-SpecMine-research'})
    batches=sorted(int(p.parent.name.split('_')[1]) for p in ROOT.glob('batch_*/sample.csv'))
    work=deque([(batch,False) for batch in batches]+[(batch,True) for batch in batches])
    model_stop=('independent_review_required' if core.cohort_overlay.reference_trial_required(ROOT)
                else None)
    if model_stop:
        print('Paid overnight dispatch locked pending the independent reference trial.',flush=True)
    github_stop=None
    model_phase_started=False
    try:
        for pass_number in range(args.max_passes):
            rows=ledger()
            if money(rows)>args.max_grok_spend or len(rows)>args.max_grok_requests:
                stop='existing_api_ledger_exceeds_hard_limits'
                break
            if model_stop is None:
                if len(rows)==args.max_grok_requests:model_stop='grok_lifetime_limit'
                elif money(rows)>=args.max_grok_spend:model_stop='grok_spending_limit'
                elif args.max_new_model_calls==0:model_stop='grok_disabled_by_configuration'
                elif not mode_allowed(rows,args.max_grok_requests,args.max_grok_spend):
                    model_stop='missing_XAI_API_KEY'
                if model_stop:print('Paid work stopped:',model_stop,flush=True)
            if work and work[0][1] and not model_phase_started and not model_stop:
                model_phase_started=True
                if (saved_quality_block(evidence_v5=True) if args.evidence_v5 else saved_quality_block()):
                    model_stop='model_quality_fallback'
                    print('Paid work skipped: saved model-quality validation window remains tripped',flush=True)
                elif args.prioritize_low_cost:
                    work=deque(sorted(work,key=lambda task:model_batch_priority(task[0])))
            while work and work[0][1] and model_stop:
                work.popleft()
            if not work:
                stop=model_stop or github_stop or 'no_useful_actionable_work'
                break
            batch,hybrid=work.popleft()
            fetch=not hybrid and not github_stop and read_count(CACHE)<args.github_limit
            if not hybrid and not fetch and not github_stop:
                github_stop='github_cumulative_limit'
            if fetch:
                status=quota(session)
                state['quota_checks']+=1
                write_json(D/f'quota_{pass_number:02d}.json',status)
                if not status['allowed']:
                    if wait_for_quota(status,state,D,args.wait_for_reset):
                        work.appendleft((batch,hybrid))
                        continue
                    github_stop=status['reason']
                    fetch=False
            command=child_command(batch,args.github_limit,hybrid,args.max_grok_requests,
                                  args.max_new_model_calls,args.max_grok_spend,fetch,
                                  args.prioritize_low_cost)
            if hybrid and args.evidence_v5:command.append('--evidence-v5')
            mode='hybrid' if hybrid else 'deterministic_only'
            print(f'Pass {pass_number+1}: batch {batch}, {mode}; GitHub fetch {fetch}; '
                  f'lifetime model attempts {len(rows)}/{args.max_grok_requests}',flush=True)
            event={'pass':pass_number+1,'batch':batch,'mode':mode,'github_fetch':fetch,
                   'before_attempts':len(rows),'before_github':read_count(CACHE)}
            events.append(event)
            write_json(D/'state.json',state)
            stop_file=ROOT/'stop_status.json'
            old_stop_time=stop_file.stat().st_mtime_ns if stop_file.exists() else None
            with (D/f'pass_{pass_number:02d}.log').open('w',encoding='utf-8') as log:
                result=subprocess.run(command,cwd=HERE.parent.parent,stdout=log,stderr=subprocess.STDOUT,text=True)
            event.update(returncode=result.returncode,after_attempts=len(ledger()),
                         after_github=read_count(CACHE))
            progress=json.loads((ROOT/'progress.json').read_text())
            event['progress']=progress
            print('Main outcomes:',progress['main'],'stop status:',result.returncode,flush=True)
            if result.returncode or progress.get('execution',{}).get('completion_status')=='github_quota_paused':
                if not stop_file.exists() or stop_file.stat().st_mtime_ns==old_stop_time:
                    stop='unclassified_child_failure; inspect pass log'
                    break
                reason=json.loads(stop_file.read_text()).get('reason','unknown_child_error')
                event['stop_reason']=reason
                if reason in {'stopped_request_limit','stopped_spending_limit'} and hybrid:
                    model_stop=reason
                    print('Paid work stopped:',reason,flush=True)
                    work.appendleft((batch,False))
                    continue
                if reason=='github_low_quota' or reason.startswith(('github_http_403','github_http_429')):
                    refreshed=quota(session)
                    state['quota_checks']+=1
                    if wait_for_quota(refreshed,state,D,args.wait_for_reset):
                        work.appendleft((batch,hybrid))
                        continue
                    if reason=='github_low_quota':
                        if not refreshed['allowed']:
                            github_stop=refreshed['reason']
                        work.appendleft((batch,hybrid))
                        continue
                stop=reason
                break
            if hybrid:
                resources=progress.get('resources',{})
                if progress.get('model_quality_fallback'):
                    model_stop='model_quality_fallback'
                elif resources.get('grok_transport_blocked_invalid_argument'):
                    model_stop='model_transport_blocked_invalid_argument'
                if model_stop:
                    print('Paid work stopped:',model_stop,flush=True)
                elif (event['after_attempts']>event['before_attempts']
                      and progress.get('verification_states',{}).get('waiting_grok_classification',0)):
                    # Give every other batch a turn before spending another pass here.
                    work.append((batch,True))
            write_json(D/'state.json',state)
            if progress['main']['unknown']==0:
                stop='all_outcomes_resolved'
                break
    except KeyboardInterrupt:
        stop='interrupted'
    except Exception as exc:
        stop='unexpected_supervisor_'+type(exc).__name__
        raise
    finally:
        state['model_stop_reason']=model_stop
        state['github_stop_reason']=github_stop
        protect_prior();state['stop_reason']=stop;state['final_main']=json.loads((ROOT/'progress.json').read_text())['main'];state['lifetime_attempts']=len(ledger());state['charged_or_reserved_usd']=money(ledger());state['github_used']=read_count(CACHE)
        state['new_resolved']=state['final_main']['positive']+state['final_main']['negative']-before['positive']-before['negative']
        state['new_positive']=state['final_main']['positive']-before['positive'];state['new_negative']=state['final_main']['negative']-before['negative'];state['unknown_delta']=state['final_main']['unknown']-before['unknown']
        write_json(D/'state.json',state);print(json.dumps(state,indent=2))
if __name__=='__main__':
    with portalocker.Lock(str(HERE/'.overnight.lock'),timeout=.1):main()
