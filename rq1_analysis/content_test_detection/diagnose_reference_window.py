import sys,json,base64,shutil,re
sys.path.insert(0,'rq1_analysis/content_test_detection')
from common import CACHE,OUT,sha256,write_json
from grok import Classification,sanitize
D=OUT/'scale100/incident_references';D.mkdir(exist_ok=True)
if not (D/'prior_scale100').exists():shutil.copytree(OUT/'scale100',D/'prior_scale100',ignore=shutil.ignore_patterns('incident_*'))
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts'];rows=[]
contents={};metas={}
for p in (CACHE/'github').glob('*.json'):
 r=json.loads(p.read_text());a=r['request']['args']
 if r['request']['kind']=='content' and r.get('ok'):
  contents[sha256(base64.b64decode(r['data']['content']))]=a
 if r['request']['kind']=='metadata' and r.get('ok'):metas[(a['repository_full_name'],r['data']['head_sha'])]=a['pr_number']
for attempt in ledger[-10:]:
 p=CACHE/'grok'/(attempt['task']+'.json');r=json.loads(p.read_text());diag=r.get('diagnostic',{});a=contents[r['content_sha256']];text=(OUT/'content'/(r['content_sha256']+'.txt')).read_text(encoding='utf-8-sig');safe,_=sanitize(text)
 raw=diag.get('raw_output');value=Classification.model_validate_json(raw).model_dump() if raw else {k:r[k] for k in Classification.model_fields}
 refs=value['evidence'] if raw else r.get('evidence_references',value['evidence']);checks=[]
 for e in refs:
  m=re.fullmatch(r'L(\d+):(.*)',e)
  checks.append({'reference':e,'source_line':safe.splitlines()[int(m[1])-1] if m and int(m[1])<=len(safe.splitlines()) else None,'quoted_tail_exact_on_line':bool(m and int(m[1])<=len(safe.splitlines()) and m[2] in safe.splitlines()[int(m[1])-1])})
 row={'key':p.stem,'repo':a['repository_full_name'],'pr':metas[(a['repository_full_name'],a['ref'])],'path':a['path'],'hash':r['content_sha256'],'live':True,'status':r['status'],'finish':diag.get('finish_reason',r.get('finish_reason')),'schema_passed':True,'classification':value['classification'],'error':diag.get('validation_message'),'prompt_version':r['prompt_version'],'validator_version':'v2-line-symbol','checks':checks};rows.append(row)
write_json(D/'ten_decisions.json',rows);write_json(D/'cost.json',{'attempts':len(ledger),'cost':sum(r.get('reported_cost_usd',0) for r in ledger)})
print(json.dumps(rows,indent=2));print('COST',len(ledger),sum(r.get('reported_cost_usd',0) for r in ledger))
