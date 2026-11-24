import json
import pandas as pd
import scale100 as s
from common import write_json,protect_prior,CACHE,OUT
sample=pd.read_csv(s.DEST/'sample100.csv');s.DEST=s.DEST/'incident_haskell';(s.DEST/'checkpoints').mkdir(exist_ok=True)
before={p:p.read_bytes() for root in [CACHE/'grok',CACHE/'repair_smoke/grok',CACHE/'github',CACHE/'offline_revalidated'] for p in root.glob('*.json')}
d,a,q=s.run_rows(sample,s.Resolver(dry_run=True))
d.to_csv(s.DEST/'offline_pr_outcomes.csv',index=False);a.to_csv(s.DEST/'offline_inspection_audit.csv',index=False)
assert all(p.read_bytes()==raw for p,raw in before.items())
protect_prior()
write_json(s.DEST/'offline_validation.json',{'summary':s.summary(d,a),'cached_records_unchanged':len(before),'prior_work_integrity':'passed','new_paid_calls':0,'pending_github_frontiers':len(q)})
print(json.dumps(s.summary(d,a),indent=2))
