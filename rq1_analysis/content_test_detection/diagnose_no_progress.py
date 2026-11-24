import json
from argparse import Namespace
from common import OUT,CACHE,write_json,sha256,protect_prior
import grok,scale100 as e,full_cohort as f
import pandas as pd
D=OUT/'full_cohort/incident_no_progress';circuit=OUT/f'full_cohort/circuit_state_{grok.PROMPT_VERSION}.json';copy=D/'window.json';copy.write_bytes(circuit.read_bytes())
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts'];args=Namespace(github_limit=1500,max_grok_requests=100,fetch_github=True,live=True,deterministic_only=False)
r=e.Resolver(dry_run=True,budget=e.ScalingBudget(max_requests=min(100,len(ledger)+10)),fallback_on_quality=True,circuit_path=copy)
resources=f.resource_status(args,r);states=pd.read_csv(OUT/'full_cohort/batch_0001/progress_states.csv');counts={}
for row in states[states.actionable_now].to_dict('records'):
 reason=f.resource_block_reason(row['verification_state'],resources['github_remaining'],True,not r.model_disabled)
 counts[reason or 'can_attempt']=counts.get(reason or 'can_attempt',0)+1
write_json(D/'diagnosis.json',{'resources':resources,'actionable_partition':counts,'source':'Saved state and cache-only constructor; no execution of cohort or network'})
manifest=json.loads((D/'preserved.json').read_text());from pathlib import Path
assert all(sha256(Path(p).read_bytes())==h for p,h in manifest.items());protect_prior();write_json(D/'integrity.json',{'status':'passed','preserved_output_files':len(manifest),'frozen_prior_work':'passed','new_repository_requests':0,'new_paid_calls':0});print(json.dumps({'resources':resources,'partition':counts},indent=2))
