import json
from common import OUT,sha256,write_json
D=OUT/'full_cohort/incident_role';D.mkdir(exist_ok=True)
paths=[p for p in (OUT/'full_cohort').rglob('*') if p.is_file() and not p.is_relative_to(D)]
write_json(D/'before_hashes.json',{str(p):sha256(p.read_bytes()) for p in paths})
w=json.loads((OUT/'full_cohort/circuit_state_content-grok-v4-required-reference.json').read_text());write_json(D/'window.json',w)
print([(r['repo'],r['pr'],r['path'],r['failed'],(r.get('diagnostic') or {}).get('validation_message')) for r in w]);l=json.loads((OUT/'api_ledger.json').read_text())['attempts'];print(len(l),sum(r.get('reported_cost_usd',0) for r in l))
