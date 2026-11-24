import json,hashlib,argparse
from pathlib import Path
import pandas as pd
from common import OUT,BASE,KEY,sha256,write_json,protect_prior
from storage import Store,git_blob_sha,metadata_request
from detector import eligible
from cohort_overlay import read_delta, VERSION
p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=OUT/'full_cohort/incident_integrity');p.add_argument('--cohort-csv',type=Path,default=OUT/'full_cohort/current_main_outcomes.csv');args=p.parse_args()
D=args.output_dir;D.mkdir(parents=True,exist_ok=True);main=pd.read_csv(args.cohort_csv);known=main[main.test_added_content_verified.notna()];store=Store()
frames=[pd.read_csv(OUT/'full_cohort/inputs/reconciled_inspection_audit.csv')]
for p in (OUT/'full_cohort').glob('batch_*/audits/*.csv'):
 try:frames.append(pd.read_csv(p))
 except pd.errors.EmptyDataError:pass
if not read_delta(OUT/'full_cohort').empty:
 frames.append(pd.read_csv(OUT/'full_cohort'/VERSION/'verified_delta_evidence.csv'))
for p in (OUT/'full_cohort'/VERSION/'ai-assisted-source-v1'/'resolved').glob('*.json'):
 try:frames.append(pd.read_csv(p.parent.parent/'audits'/p.with_suffix('.csv').name))
 except pd.errors.EmptyDataError:pass
audits=pd.concat(frames,ignore_index=True).drop_duplicates(KEY+['file_path'],keep='last');grouped={k:g for k,g in audits.groupby(KEY)}
checks=[];issues=[]
for r in known.to_dict('records'):
 key=(r['repo_name'],int(r['pr_number']));metadata=store.data(metadata_request(*key));files,complete,_,_=store.files(*key)
 try:
  assert complete and metadata['head_sha']==r['pinned_commit_sha'],'metadata/head incomplete or different'
  bypath={x['filename']:x for x in files}
  if r['test_added_content_verified']==1:
   f=bypath[r['confirmed_file_path']];assert f['status']=='added'
   raw=(OUT/'content'/(r['file_content_hash']+'.txt')).read_bytes();assert sha256(raw)==r['file_content_hash'] and git_blob_sha(raw)==f['sha'],'positive hash failure'
  else:
   assert str(r['inspection_complete']).lower()=='true'
   expected={f['filename']:f for f in files if f['status']=='added' and eligible(f['filename'])}
   g=grouped.get(key,pd.DataFrame());proof={x['file_path']:x for x in g.to_dict('records')}
   for path,f in expected.items():
    a=proof[path];assert a['classification'] in {'not_test','test_support'} and str(a['examined']).lower()=='true','negative classification incomplete'
    raw=(OUT/'content'/(a['content_sha256']+'.txt')).read_bytes();assert sha256(raw)==a['content_sha256'] and git_blob_sha(raw)==f['sha'],'negative hash failure'
  checks.append({'repo_name':key[0],'pr_number':key[1],'outcome':int(r['test_added_content_verified']),'status':'passed'})
 except (AssertionError,KeyError,FileNotFoundError) as exc:issues.append({'repo_name':key[0],'pr_number':key[1],'reason':str(exc)})
pd.DataFrame(checks).to_csv(D/'resolved_integrity_audit.csv',index=False);write_json(D/'resolved_integrity_issues.json',issues)
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts']
write_json(D/'reconciliation.json',{'resolved':len(known),'passed':len(checks),'issues':issues,'positive':int(known.test_added_content_verified.sum()),'negative':int(known.test_added_content_verified.eq(0).sum()),'unknown':int(main.test_added_content_verified.isna().sum()),'model_attempts':len(ledger),'model_cost':sum(x.get('reported_cost_usd',0) for x in ledger)})
protect_prior();print(json.dumps({'resolved':len(known),'passed':len(checks),'issues':issues},indent=2))
