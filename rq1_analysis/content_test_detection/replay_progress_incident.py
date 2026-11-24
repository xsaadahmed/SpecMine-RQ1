import json
import pandas as pd
import scale100 as e
import full_cohort as f
from progress_audit import audit_pending
from common import OUT,CACHE,KEY,sha256,write_json,protect_prior
D=OUT/'full_cohort/incident_progress';sample=pd.read_csv(f.DEST/'batch_0001/sample.csv');old=pd.read_csv(f.DEST/'batch_0001/outcomes.csv');groups=f.groups()
known=old[old.test_added_content_verified.notna()].copy();unknown=sample.merge(old[KEY+['test_added_content_verified']],on=KEY);unknown=unknown[unknown.test_added_content_verified.isna()]
e.DEST=D/'offline_search';(e.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
before={p:sha256(p.read_bytes()) for root in [CACHE/'github',CACHE/'grok',CACHE/'offline_revalidated',CACHE/'repair_smoke/grok'] for p in root.glob('*.json')}
new,a,q=e.run_rows(unknown,e.Resolver(dry_run=True),groups=groups)
combined=pd.concat([known,new],ignore_index=True).drop_duplicates(KEY)
combined.to_csv(D/'offline_outcomes.csv',index=False);a.to_csv(D/'offline_inspection_audit.csv',index=False)
states=audit_pending(sample,combined,groups,e.Resolver(dry_run=True));states.to_csv(D/'progress_states.csv',index=False)
summary=e.summary(combined,a);summary['pending_actionable']=int(states.actionable_now.sum());summary['blocked_unknown']=int((states.resumable&~states.actionable_now).sum());summary['states']=states.verification_state.value_counts().to_dict()
# Summary methods cover only the unknown replay; original known audit is kept separately.
summary['audit_scope']='Replayed previously unknown PRs only; known 14 outcomes reused'
write_json(D/'offline_summary.json',summary)
assert all(sha256(p.read_bytes())==h for p,h in before.items());protect_prior()
manifest=json.loads((D/'preserved_manifest.json').read_text());assert all(sha256((D/'prior_outputs'/p.replace('\\','/').removeprefix('full_cohort/')).read_bytes())==h for p,h in manifest.items())
write_json(D/'integrity.json',{'cache_records_unchanged':len(before),'preserved_output_files':len(manifest),'prior_work':'passed','new_paid_calls':0})
print(json.dumps(summary,indent=2))
