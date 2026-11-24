import json
import pandas as pd
import full_cohort as f,scale100 as e
from progress_audit import audit_pending
from common import OUT,KEY,CACHE,write_json,sha256,protect_prior
D=OUT/'full_cohort/overnight_preparation';sample=pd.read_csv(f.DEST/'batch_0001/sample.csv');old=pd.read_csv(f.DEST/'batch_0001/outcomes.csv');known=old[old.test_added_content_verified.notna()];pending=sample.merge(old[KEY+['test_added_content_verified']],on=KEY);pending=pending[pending.test_added_content_verified.isna()]
e.DEST=D/'batch1_replay';(e.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
d,a,q=e.run_rows(pending,e.Resolver(dry_run=True),groups=f.groups());combined=pd.concat([known,d],ignore_index=True);combined.to_csv(D/'batch1_offline_outcomes.csv',index=False);a.to_csv(D/'batch1_offline_audit.csv',index=False)
states=audit_pending(sample,combined,f.groups(),e.Resolver(dry_run=True));states.to_csv(D/'batch1_states.csv',index=False)
order=f.prioritize_remaining(sample,states);order[order[KEY].apply(tuple,axis=1).isin(set(map(tuple,pending[KEY].to_numpy())))].to_csv(D/'batch1_remaining_priority.csv',index=False)
write_json(D/'batch1_replay_summary.json',e.summary(combined,a))
# Prepare, but do not process, the next disjoint stratified draw.
entry=pd.read_csv(f.DEST/'entry_cohort.csv');f.BATCH='batch_0002';_,batch2=f.make_queue(entry);f.protect_selection()
class Args:github_limit=7500;max_grok_requests=100
write_json(D/'batch2_estimate.json',f.estimate(batch2,f.groups(),Args()))
manifest=json.loads((D/'preserved.json').read_text());from pathlib import Path
assert all(sha256(Path(p).read_bytes())==h for p,h in manifest.items());protect_prior();write_json(D/'integrity.json',{'prior_outputs_unchanged':len(manifest),'frozen_prior_work':'passed','new_paid_calls':0,'new_github_reads':0})
print(json.dumps({'batch1':e.summary(combined,a),'states':states.verification_state.value_counts().to_dict(),'batch2_selected':len(batch2),'batch2_repositories':batch2.repo_name.nunique()},indent=2))
