import json,csv
import pandas as pd
from common import OUT,CACHE,BASE,write_json,sha256,protect_prior
from storage import Store,metadata_request
from detector import eligible
D=OUT/'full_cohort';D.mkdir(exist_ok=True)
d=pd.read_csv(OUT/'scale100/pr_outcomes.csv');a=pd.read_csv(OUT/'scale100/inspection_audit.csv');store=Store();rows=[]
raw=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=['repo_name','pr_number','file_path','change_status'])
for r in d[d.test_added_content_verified.isna()].to_dict('records'):
 repo,num=r['repo_name'],int(r['pr_number']);files,complete,pending,reason=store.files(repo,num)
 expected=raw[raw.repo_name.eq(repo)&raw.pr_number.eq(num)]
 category='missing_metadata_or_file_pages' if not complete else 'changed_PR_diff' if {(x.file_path,x.change_status) for x in expected.itertuples()}!={(f['filename'],f['status']) for f in files} else 'unresolved_content_classification'
 uncertain=a[a.repo_name.eq(repo)&a.pr_number.eq(num)&a.classification.eq('uncertain')]
 details=[]
 for f in uncertain.to_dict('records'):
  decisions=[x for root in [CACHE/'grok',CACHE/'repair_smoke/grok'] for p in root.glob('*.json') if (x:=json.loads(p.read_text())).get('content_sha256')==f.get('content_sha256')]
  details.append({'path':f['file_path'],'static_reason':f.get('classification_reason'),'model_errors':[x.get('diagnostic',{}).get('validation_message','unrecorded legacy reason') for x in decisions]})
 if complete and category!='changed_PR_diff':
  meta=store.data(metadata_request(repo,num));missing=[]
  for f in files:
   if f['status']=='added' and eligible(f['filename']):
    text,prov,request=store.content(repo,meta['head_sha'],f['filename'],f.get('sha'))
    if text is None:missing.append({'path':f['filename'],'status':prov.get('status')})
  if missing:details.append({'missing_contents':missing});category='missing_file_contents' if not len(uncertain) else 'missing_contents_and_unresolved_classification'
 rows.append({'repo_name':repo,'pr_number':num,'category':category,'file_list_complete':complete,'pending_requests':len(pending),'details':json.dumps(details),'note':'No negative inferred. Latest cache may contain metadata acquired after frozen 100-PR summary.'})
pd.DataFrame(rows).to_csv(D/'six_unknowns.csv',index=False)
# Preserve every previous official 100-PR output byte, including its archived incidents.
manifest=D/'protected_100pr_outputs.json'
if not manifest.exists():write_json(manifest,{str(p.relative_to(OUT)):sha256(p.read_bytes()) for p in (OUT/'scale100').rglob('*') if p.is_file()})
print(pd.DataFrame(rows)[['repo_name','pr_number','category']].to_string(index=False));protect_prior()
