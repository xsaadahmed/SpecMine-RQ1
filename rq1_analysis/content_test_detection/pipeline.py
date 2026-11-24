"""Cached-file evaluation, prioritized PR search, frontiers, and cohort queue."""
from collections import Counter
import json
from pathlib import PurePosixPath

import pandas as pd

from common import BASE,CACHE,HIST,KEY,OLD,OUT,sha256,stable_hash,write_json
from detector import VERSION,classify,eligible,language,priority
from grok import GrokResolver,usage_report
from storage import Store,cached_review_text,content_request,metadata_request


def static_prediction(text,path,raw_hash):
    context=f'{language(path)}|{PurePosixPath(path).suffix.lower()}|{priority(path)<2}'
    if PurePosixPath(path).name == '.npmrc':
        context += '|npmrc-boolean-v1'
    if PurePosixPath(path).name.lower().endswith('.tests.ps1'):
        context += '|standalone-powershell-v1'
    key=sha256(f'{raw_hash}|{VERSION}|{context}'.encode())
    file=CACHE/'deterministic'/(key+'.json')
    if file.exists():return json.loads(file.read_text())
    value=classify(text,path)
    for e in value['evidence']:
        if e['symbol'] not in text:
            value.update(classification='uncertain',has_executable_tests=None,needs_review=True,reason='Deterministic evidence could not be located verbatim')
    value['content_sha256']=raw_hash;value['evidence_reference']=file.relative_to(BASE.parent).as_posix()
    write_json(file,value,immutable=True);return value


def hybrid(text,path,raw_hash,grok):
    deterministic=getattr(grok,'static_classifier',static_prediction)(text,path,raw_hash)
    if deterministic['classification']!='uncertain':return deterministic,None
    ai=grok.resolve(text,path,deterministic['language'],raw_hash)
    if ai.get('status')=='validated' and not ai['needs_review']:
        value={**ai,'evidence_reference':(CACHE/'grok'/(ai['cache_key']+'.json')).relative_to(BASE.parent).as_posix(),'full_content_examined':ai.get('complete_input',True)}
        return value,ai
    return deterministic,ai


def evaluate_files(grok):
    frame=pd.read_csv(HIST/'outputs/human_review.csv')
    records=[]
    for r in frame.to_dict('records'):
        text=cached_review_text(r)
        deterministic=static_prediction(text,r['file_path'],r['content_sha256'])
        value,ai=hybrid(text,r['file_path'],r['content_sha256'],grok)
        old=OLD.classify_test_file(r['file_path'])
        new=value['has_executable_tests'] if not value['needs_review'] else None
        records.append({**{k:r[k] for k in ['review_id','pilot_id','repo_name','pr_number','file_path','commit_sha','content_sha256','content_reference']},'old_path_is_test':old[0],'old_path_reason':old[1],'old_path_uncertain':old[2],'deterministic_classification':deterministic['classification'],'grok_classification':ai.get('classification') if ai else None,'grok_status':ai.get('status') if ai else 'not_needed','hybrid_classification':value['classification'],'has_executable_tests':new,'classification_method':value['method'],'evidence':json.dumps(value['evidence'],ensure_ascii=False),'reason':value['reason'],'evidence_reference':value['evidence_reference'],'path_vs_content_disagreement':bool(old[0]!=new) if new is not None else None,'likely_error':None if new is None or old[0]==new else 'path_false_negative_candidate' if new else 'path_false_positive_candidate','independent_human_reference':False})
    d=pd.DataFrame(records)
    d.to_csv(OUT/'file_classification_results.csv',index=False)
    d[d.path_vs_content_disagreement.eq(True)].to_csv(OUT/'tables/file_detector_disagreements.csv',index=False)
    write_json(OUT/'file_evaluation_summary.json',{'n_files':len(d),'deterministic_classes':d.deterministic_classification.value_counts().to_dict(),'hybrid_classes':d.hybrid_classification.value_counts().to_dict(),'determinate_disagreements':int(d.path_vs_content_disagreement.eq(True).sum()),'uncertain_cases':int(d.has_executable_tests.isna().sum()),'new_github_requests':0,'precision':None,'recall':None,'accuracy':None,'reference_status':'No independent human labels; these are detector comparisons only'})
    return d


def search_pr(files,fetch,classify_file,file_list_complete=True,blocked_reason=None):
    """Pure PR search. Unknowns never become zeros; one positive stops immediately.

    fetch returns (text, provenance, pending_request). Only added eligible files
    enter the search, including sources outside conventional test locations.
    """
    candidates=sorted([f for f in files if f['status']=='added' and eligible(f['filename'])],key=lambda f:(priority(f['filename']),f['filename']))
    inspected=[];pending=[];ambiguous=0;attempted=0
    if blocked_reason:
        return {'test_added_content_verified':None,'unknown_reason':blocked_reason,'n_eligible_added_files':len(candidates),'n_files_inspected':0,'n_files_attempted':0,'files_avoided_early_exit':0,'inspection_complete':False},inspected,pending
    for index,f in enumerate(candidates):
        text,provenance,req=fetch(f)
        if req is not None:pending.append(req);continue
        attempted+=1
        if text is None:
            inspected.append({'file_path':f['filename'],'retrieval_status':provenance.get('status'),'examined':False,'classification':'uncertain'})
            ambiguous+=1;continue
        value=classify_file(text,f,provenance)
        known=value.get('has_executable_tests') if not value.get('needs_review',True) else None
        inspected.append({'file_path':f['filename'],'retrieval_status':'verified','examined':True,'classification':value['classification'],'classification_method':value['method'],'classification_reason':value['reason'] if 'reason' in value else None,'needs_review':value.get('needs_review'),'evidence_reference':value.get('evidence_reference'),**provenance})
        if known is True:
            return {'test_added_content_verified':1,'unknown_reason':None,'confirmed_file_path':f['filename'],'commit_sha':provenance.get('commit_sha'),'file_content_hash':provenance.get('content_sha256'),'test_detection_method':value['method'],'test_detection_evidence':value.get('evidence_reference'),'supporting_evidence':json.dumps(value['evidence'],ensure_ascii=False),'n_eligible_added_files':len(candidates),'n_files_inspected':sum(x['examined'] for x in inspected),'n_files_attempted':attempted,'files_avoided_early_exit':len(candidates)-attempted,'inspection_complete':False,'early_exit':True},inspected,[]
        if known is None:ambiguous+=1
    positive=False
    complete=file_list_complete and not pending and ambiguous==0
    return {'test_added_content_verified':0 if complete else None,'unknown_reason':None if complete else 'missing_content_or_unresolved_classification' if file_list_complete else 'incomplete_file_list','n_eligible_added_files':len(candidates),'n_files_inspected':sum(x['examined'] for x in inspected),'n_files_attempted':attempted,'files_avoided_early_exit':0,'inspection_complete':complete,'early_exit':False,'test_detection_method':'deterministic' if inspected and all(x.get('classification_method')=='deterministic' for x in inspected) else 'combined' if inspected else 'deterministic_empty_added_source_set' if complete else None},inspected,pending[:1]


def selected_main_subset(n=24):
    target=OUT/'main_acquisition_subset.csv'
    if target.exists():
        parts=[pd.read_csv(target)]+[pd.read_csv(p) for p in sorted((OUT/'main_batches').glob('*.csv'))] if (OUT/'main_batches').exists() else [pd.read_csv(target)]
        return pd.concat(parts,ignore_index=True).drop_duplicates(KEY)
    d=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    pilot=pd.read_csv(HIST/'outputs/pilot_sample.csv')[KEY]
    others=d.merge(pilot.assign(in_pilot=True),on=KEY,how='left')
    others=others[others.in_pilot.isna()].copy()
    others['rank']=[stable_hash(f'{r}|{number}') for r,number in zip(others.repo_name,others.pr_number)]
    others['stratum']=others.tool+'|'+others.has_acceptance_criteria.astype(int).astype(str)+'|'+others.test_added.astype(int).astype(str)
    # Repository/tool diversity through round-robin stratum ranks; not a random
    # population sample for statistical inference. All remaining PRs stay queued.
    others=others.sort_values('rank');others['within_stratum_rank']=others.groupby('stratum').cumcount()
    selected=others.sort_values(['within_stratum_rank','rank']).head(n)
    selected.to_csv(target,index=False);return selected


def extend_main_subset(n):
    """Activate another frozen, reproducible acquisition batch without erasing old draws."""
    selected=selected_main_subset()
    d=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    p=pd.read_csv(HIST/'outputs/pilot_sample.csv')
    used=set(map(tuple,p[KEY].to_numpy()))|set(map(tuple,selected[KEY].to_numpy()))
    d=d[[tuple(x) not in used for x in d[KEY].to_numpy()]].copy()
    d['selection_hash']=[stable_hash(f'{r}|{number}') for r,number in zip(d.repo_name,d.pr_number)]
    batch=d.sort_values('selection_hash').head(n)
    directory=OUT/'main_batches';directory.mkdir(exist_ok=True)
    target=directory/f'batch_{len(list(directory.glob("*.csv")))+1:04d}.csv'
    if len(batch):batch.to_csv(target,index=False)
    return len(batch)


def process_prs(scope,grok,store=None):
    store=store or Store()
    main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    pilot=pd.read_csv(HIST/'outputs/pilot_sample.csv')
    frame=pilot if scope=='pilot' else main
    rawfiles=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=KEY+['file_path','change_status'])
    grouped={key:g for key,g in rawfiles.groupby(KEY)}
    results=[];audits=[];queue=[]
    acquisition_set=set(map(tuple,selected_main_subset()[KEY].to_numpy())) if scope=='main' else set(map(tuple,pilot[KEY].to_numpy()))
    pilot_keys=set(map(tuple,pilot[KEY].to_numpy()))
    for row in frame.to_dict('records'):
        repo,num=row['repo_name'],int(row['pr_number']);key=(repo,num)
        meta=store.data(metadata_request(repo,num))
        files,complete,reqs,reason=store.files(repo,num)
        allowed=scope=='pilot' or key in acquisition_set or key in pilot_keys
        base={'repo_name':repo,'pr_number':num,'tool':row['tool'],'repo_language':row.get('repo_language'),'test_added':row['test_added'],'eligible_for_new_acquisition':allowed}
        if files is None or meta is None:
            expected=grouped.get(key,pd.DataFrame())
            n_eligible=sum(eligible(r.file_path) and r.change_status=='added' for r in expected.itertuples()) if len(expected) else 0
            results.append({**base,'test_added_content_verified':None,'unknown_reason':reason,'n_eligible_added_files':n_eligible,'n_files_inspected':0,'n_files_attempted':0,'files_avoided_early_exit':0,'inspection_complete':False,'pinned_commit_sha':None,'file_list_complete':False})
            if allowed:queue.extend(reqs)
            continue
        expected=grouped.get(key)
        aligned=expected is not None and {(r.file_path,r.change_status) for r in expected.itertuples()}=={(f['filename'],f['status']) for f in files}
        def fetch(f):return store.content(repo,meta['head_sha'],f['filename'],f.get('sha'))
        def classify_file(text,f,provenance):return hybrid(text,f['filename'],provenance['content_sha256'],grok)[0]
        outcome,audit,pending=search_pr(files,fetch,classify_file,complete,blocked_reason='net_diff_changed_from_frozen_study' if complete and not aligned else None)
        outcome.update(base,pinned_commit_sha=meta['head_sha'],file_list_complete=complete,aligned_with_frozen_file_set=aligned)
        for a in audit:audits.append({**base,**a})
        if allowed:queue.extend(reqs or pending)
        # Store a durable checkpoint after each PR. Replays reuse content and
        # classifier caches; counts describe unique paths within this search.
        write_json(CACHE/('checkpoint_'+stable_hash(f'{repo}|{num}')[:20]+'.json'),outcome)
        results.append(outcome)
    d=pd.DataFrame(results)
    d['test_added_content_verified']=pd.array(d.test_added_content_verified,dtype='Int64')
    d.to_csv(OUT/f'{scope}_pr_outcomes.csv',index=False)
    if scope=='main':d[d.test_added_content_verified.isna()].to_csv(OUT/'main_resumable_queue.csv',index=False)
    pd.DataFrame(audits).to_csv(OUT/f'{scope}_inspection_audit.csv',index=False)
    q=list({r['id']:r for r in queue if store.record(r) is None}.values())
    write_json(OUT/f'{scope}_github_frontier.json',q)
    known=d.test_added_content_verified.notna()
    summary={'n_prs':len(d),'confirmed_added_tests':int(d.test_added_content_verified.eq(1).sum()),'confident_no_added_tests':int(d.test_added_content_verified.eq(0).sum()),'unknown':int(d.test_added_content_verified.isna().sum()),'total_files_inspected':int(d.n_files_inspected.sum()),'mean_files_inspected_per_pr':float(d.n_files_inspected.mean()),'median_files_inspected_per_pr':float(d.n_files_inspected.median()),'eligible_added_files':int(d.n_eligible_added_files.sum()),'files_avoided_early_exit':int(d.files_avoided_early_exit.sum()),'determinate_path_disagreements':int(d.loc[known,'test_added'].astype(int).ne(d.loc[known,'test_added_content_verified'].astype(int)).sum()),'pending_frontier_requests':len(q),'confirmed_method_counts':d.loc[d.test_added_content_verified.eq(1),'test_detection_method'].value_counts().to_dict() if 'test_detection_method' in d else {},'uninspected_prs_are_negative':False}
    write_json(OUT/f'{scope}_pr_summary.json',summary)
    return d,q


def save_grok_plan(grok):
    write_json(OUT/'grok_dry_run_plan.json',list(grok.pending.values()))
    write_json(OUT/'api_usage_report.json',usage_report(grok.budget))
