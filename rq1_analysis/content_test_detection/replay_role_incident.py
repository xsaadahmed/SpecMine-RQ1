import json
import pandas as pd
import scale100 as e,full_cohort as f
from common import OUT,KEY,write_json,sha256,protect_prior
D=OUT/'full_cohort/incident_role';sample=pd.read_csv(f.DEST/'batch_0001/sample.csv');old=pd.read_csv(f.DEST/'batch_0001/outcomes.csv');known=old[old.test_added_content_verified.notna()];pending=sample.merge(old[KEY+['test_added_content_verified']],on=KEY);pending=pending[pending.test_added_content_verified.isna()]
e.DEST=D/'replay';(e.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
d,a,q=e.run_rows(pending,e.Resolver(dry_run=True),groups=f.groups());allrows=pd.concat([known,d],ignore_index=True);allrows.to_csv(D/'offline_outcomes.csv',index=False);a.to_csv(D/'offline_audit.csv',index=False)
write_json(D/'offline_summary.json',e.summary(allrows,a));print(json.dumps(e.summary(allrows,a),indent=2))
manifest=json.loads((D/'before_hashes.json').read_text());assert all(sha256(__import__('pathlib').Path(p).read_bytes())==h for p,h in manifest.items());protect_prior();print('All existing full-cohort output hashes preserved')
