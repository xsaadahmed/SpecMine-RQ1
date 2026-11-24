import json
from common import CACHE,OUT,sha256,write_json,protect_prior
from grok import validate_output,sanitize,VALIDATOR_VERSION
D=OUT/'scale100/incident_references';rows=json.loads((D/'ten_decisions.json').read_text());recovered=[]
for row in rows:
 old=json.loads((CACHE/'grok'/(row['key']+'.json')).read_text());raw=(OUT/'content'/(old['content_sha256']+'.txt')).read_bytes();assert sha256(raw)==old['content_sha256'];text=raw.decode('utf-8-sig');safe,_=sanitize(text)
 if old['status']=='validated':row['recovered_offline']=False;row['post_validation']='previous success retained';continue
 try:
  diag=old['diagnostic'];parsed=validate_output(diag['raw_output'],safe,diag['complete_input']);assert all(e in text for e in parsed.evidence)
  result={**old,**parsed.model_dump(),'status':'validated','complete_input':diag['complete_input'],'evidence_references':json.loads(diag['raw_output'])['evidence'],'finish_reason':diag['finish_reason'],'usage':diag['usage'],'reported_cost_usd':diag['reported_cost_usd'],'validator_version':VALIDATOR_VERSION,'offline_revalidation':{'original_cache_key':row['key'],'rule':'exact tail on exact numbered line plus executable-test context; no quote rewriting','independent_human_reference':False}}
  write_json(CACHE/'offline_revalidated'/(row['key']+'.json'),result,immutable=True);row['recovered_offline']=True;row['post_validation']='exact line/tail verified';recovered.append(row['key'])
 except ValueError as e:row['recovered_offline']=False;row['post_validation']=str(e)
write_json(D/'ten_decisions_revalidated.json',rows);protect_prior();print(json.dumps([{'repo':r['repo'],'pr':r['pr'],'path':r['path'],'recovered':r['recovered_offline'],'result':r['post_validation']} for r in rows],indent=2))
