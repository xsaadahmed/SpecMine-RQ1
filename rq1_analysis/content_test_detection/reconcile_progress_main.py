import json
import pandas as pd
from common import OUT,KEY,write_json
D=OUT/'full_cohort/incident_progress';main=pd.read_csv(OUT/'full_cohort/current_main_outcomes.csv').set_index(KEY);batch=pd.read_csv(D/'offline_outcomes.csv');corrections=json.loads((OUT/'full_cohort/known_negative_corrections.json').read_text())
for r in batch.to_dict('records')+corrections:
 k=tuple(r[x] for x in KEY)
 for col,value in r.items():
  if col in KEY:continue
  if col not in main:main[col]=None
  main.loc[k,col]=value
main=main.reset_index();main.to_csv(D/'offline_main_outcomes.csv',index=False);y=main.test_added_content_verified
write_json(D/'offline_main_summary.json',{'positive':int(y.eq(1).sum()),'negative':int(y.eq(0).sum()),'unknown':int(y.isna().sum()),'known_negative_recheck_corrections':len(corrections)})
print(json.dumps(json.loads((D/'offline_main_summary.json').read_text())))
