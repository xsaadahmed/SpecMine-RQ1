import json
from common import OUT,write_json,sha256
D=OUT/'full_cohort/overnight_preparation';D.mkdir(exist_ok=True)
paths=list((OUT/'full_cohort').glob('*.json'))+list((OUT/'full_cohort').glob('*.csv'))+list((OUT/'full_cohort/batch_0001').rglob('*'))
write_json(D/'preserved.json',{str(p):sha256(p.read_bytes()) for p in paths if p.is_file()})
print('Current research outputs fingerprinted')
