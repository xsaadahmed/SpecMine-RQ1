import json,argparse
from pathlib import Path
import pandas as pd
import full_cohort as f,scale100 as e
from progress_audit import audit_pending
from common import OUT,KEY,sha256,write_json,protect_prior
p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=OUT/'full_cohort/incident_integrity');args=p.parse_args()
D=args.output_dir;D.mkdir(parents=True,exist_ok=True);sample=pd.read_csv(f.DEST/'batch_0006/sample.csv');old=pd.read_csv(f.DEST/'batch_0006/outcomes.csv');known=old[old.test_added_content_verified.notna()];remaining=sample.merge(old[KEY+['test_added_content_verified']],on=KEY);remaining=remaining[remaining.test_added_content_verified.isna()]
e.DEST=D/'offline_replay';(e.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
new,a,q=e.run_rows(remaining,e.Resolver(dry_run=True),groups=f.groups());combined=pd.concat([known,new],ignore_index=True);combined.to_csv(D/'offline_batch6_outcomes.csv',index=False);a.to_csv(D/'offline_audit.csv',index=False)
states=audit_pending(sample,combined,f.groups(),e.Resolver(dry_run=True));states.to_csv(D/'progress_states.csv',index=False)
summary=e.summary(combined,a);summary['actionable']=int(states.actionable_now.sum());summary['blocked']=int((states.resumable&~states.actionable_now).sum());summary['states']=states.verification_state.value_counts().to_dict();write_json(D/'offline_summary.json',summary)
manifest=json.loads((D/'preserved.json').read_text());assert all(sha256(Path(p).read_bytes())==h for p,h in manifest.items());protect_prior();print(json.dumps(summary,indent=2));print('All original output fingerprints and prior-work checks pass')
