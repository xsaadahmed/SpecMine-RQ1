import json
from common import OUT,sha256,write_json
D=OUT/'full_cohort/incident_contents';D.mkdir(exist_ok=True)
write_json(D/'preserved.json',{str(p):sha256(p.read_bytes()) for p in (OUT/'full_cohort').rglob('*') if p.is_file() and not p.is_relative_to(D)})
print('Output hashes saved')
