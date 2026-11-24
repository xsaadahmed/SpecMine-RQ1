import json
import pandas as pd
from common import OUT,CACHE,sha256,write_json
from detector import classify
D=OUT/'full_cohort/incident_progress';main=pd.read_csv(OUT/'full_cohort/current_main_outcomes.csv');neg=set(map(tuple,main.loc[main.test_added_content_verified.eq(0),['repo_name','pr_number']].to_numpy()));frames=[pd.read_csv(OUT/'full_cohort/inputs/reconciled_inspection_audit.csv')]
for p in (OUT/'full_cohort/batch_0001/audits').glob('*.csv'):
 try:frames.append(pd.read_csv(p))
 except pd.errors.EmptyDataError:pass
rows=[]
for r in pd.concat(frames,ignore_index=True).drop_duplicates(['repo_name','pr_number','file_path']).to_dict('records'):
 if (r['repo_name'],r['pr_number']) not in neg or not str(r.get('file_path','')).endswith(('.cs','.java')):continue
 h=r.get('content_sha256');p=OUT/'content'/(str(h)+'.txt')
 if not p.exists():continue
 raw=p.read_bytes();assert sha256(raw)==h
 result=classify(raw.decode('utf-8-sig'),r['file_path']);rows.append({'repo_name':r['repo_name'],'pr_number':r['pr_number'],'path':r['file_path'],'classification':result['classification'],'reason':result['reason']})
pd.DataFrame(rows).to_csv(D/'negative_annotation_recheck.csv',index=False);print(json.dumps({'negative_CS_Java_files_rechecked':len(rows),'potential_positive_corrections':sum(r['classification']=='automated_test' for r in rows),'unresolved':sum(r['classification']=='uncertain' for r in rows)}))
