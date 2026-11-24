import sys,json,shutil
from pathlib import Path
sys.path.insert(0,'rq1_analysis/content_test_detection')
from common import CACHE,OUT,HIST,sha256,write_json
D=OUT/'scale100/incident_cpp';D.mkdir(exist_ok=True)
if not (D/'prior_scale100').exists():shutil.copytree(OUT/'scale100',D/'prior_scale100',ignore=shutil.ignore_patterns('incident_cpp'))
f=CACHE/'grok/31ea0bc9dfdc144465e74d78cd0a959a1485b39a912a7d2208444d10f4fb930a.json';r=json.loads(f.read_text());source=None
for p in (OUT/'content').glob('*'):
 if p.is_file() and sha256(p.read_bytes())==r['content_sha256']:source=p.read_bytes().decode('utf-8-sig')
assert source is not None
matches=[]
for p in (CACHE/'github').glob('*.json'):
 d=json.loads(p.read_text());a=d['request']['args']
 if d['request']['kind']=='content':
  import base64
  if d.get('ok') and sha256(base64.b64decode(d['data'].get('content','')))==r['content_sha256']:matches.append(a)
parsed=json.loads(r['diagnostic']['raw_output'])
checks=[{'citation':e,'present':e in source,'length':len(e)} for e in parsed['evidence']]
print(json.dumps({'matches':matches,'checks':checks},indent=2))
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts'];print({'calls':len(ledger),'cost':sum(x.get('reported_cost_usd',0) for x in ledger)})
write_json(D/'diagnosis.json',{'matches':matches,'citation_checks':checks,'attempted_classification':parsed['classification'],'recoverable':False,'calls':len(ledger),'cost':sum(x.get('reported_cost_usd',0) for x in ledger)})
