import json
from pathlib import Path
from common import OUT,sha256,protect_prior,write_json
D=OUT/'full_cohort/incident_contents';m=json.loads((D/'preserved.json').read_text());assert all(sha256(Path(p).read_bytes())==h for p,h in m.items());protect_prior();write_json(D/'integrity.json',{'existing_full_cohort_files_unchanged':len(m),'frozen_prior_work':'passed','new_paid_calls':0,'new_repository_requests':0});print('All preserved outputs and frozen integrity checks passed')
