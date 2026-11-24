import sys,json,base64,shutil
sys.path.insert(0,'rq1_analysis/content_test_detection')
from common import CACHE,OUT,sha256,write_json
D=OUT/'scale100/incident_haskell';D.mkdir(exist_ok=True)
if not (D/'prior_scale100').exists():shutil.copytree(OUT/'scale100',D/'prior_scale100',ignore=shutil.ignore_patterns('incident_haskell','incident_cpp'))
rs=[]
for p in sorted((CACHE/'grok').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:3]:
 r=json.loads(p.read_text());text=(OUT/'content'/(r['content_sha256']+'.txt')).read_text(encoding='utf-8-sig');parsed=json.loads(r['diagnostic']['raw_output']);matches=[]
 for q in (CACHE/'github').glob('*.json'):
  d=json.loads(q.read_text());a=d['request']['args']
  if d['request']['kind']=='content' and d.get('ok') and sha256(base64.b64decode(d['data'].get('content','')))==r['content_sha256']:matches.append(a)
 repo=matches[0]['repository_full_name'];head=matches[0]['ref'];pr=None
 for q in (CACHE/'github').glob('*.json'):
  d=json.loads(q.read_text())
  if d['request']['kind']=='metadata' and d.get('data',{}).get('head_sha')==head:pr=d['request']['args']['pr_number']
 checks=[{'length':len(e),'verbatim':e in text,'evidence':e} for e in parsed['evidence']]
 rs.append({'repo':repo,'pr':pr,'path':matches[0]['path'],'response_key':p.stem,'finish':r['diagnostic']['finish_reason'],'classification':parsed['classification'],'checks':checks,'cost':r['diagnostic']['reported_cost_usd']})
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts'];write_json(D/'diagnosis.json',{'failures':rs,'lifetime_attempts':len(ledger),'cumulative_cost':sum(r.get('reported_cost_usd',0) for r in ledger)})
print(json.dumps({'failures':[{**r,'checks':[{k:v for k,v in c.items() if k!='evidence'} for c in r['checks']]} for r in rs],'attempts':len(ledger),'cost':sum(r.get('reported_cost_usd',0) for r in ledger)},indent=2))
