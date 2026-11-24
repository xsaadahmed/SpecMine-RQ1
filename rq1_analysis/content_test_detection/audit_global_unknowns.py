import json
from pathlib import Path
import pandas as pd
import full_cohort as f,scale100 as e
from progress_audit import audit_pending
from common import OUT,write_json,sha256,protect_prior
D=OUT/'full_cohort/incident_integrity';main=pd.read_csv(OUT/'full_cohort/current_main_outcomes.csv');unknown=main[main.test_added_content_verified.isna()]
s=audit_pending(unknown,main,f.groups(),e.Resolver(dry_run=True));s.to_csv(D/'global_unknown_states.csv',index=False)
write_json(D/'global_pending.json',{'unknown':len(s),'actionable':int(s.actionable_now.sum()),'blocked':int((~s.actionable_now).sum()),'states':s.verification_state.value_counts().to_dict()});print(json.dumps(json.loads((D/'global_pending.json').read_text()),indent=2))
m=json.loads((D/'preserved.json').read_text());assert all(sha256(Path(p).read_bytes())==h for p,h in m.items());protect_prior();print('Original outputs remain unchanged')
