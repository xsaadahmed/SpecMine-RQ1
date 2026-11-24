import json
from common import OUT,sha256,write_json
D=OUT/'full_cohort/incident_no_progress';D.mkdir(exist_ok=True)
paths=list((OUT/'full_cohort').glob('*.json'))+list((OUT/'full_cohort').glob('*.csv'))+list((OUT/'full_cohort/batch_0001').rglob('*.csv'))
write_json(D/'preserved.json',{str(p):sha256(p.read_bytes()) for p in paths});print('Saved output fingerprints')
