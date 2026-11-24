import json
from common import OUT,CACHE,write_json,sha256,protect_prior
from grok import validate_output,sanitize,VALIDATOR_VERSION
D=OUT/'full_cohort/incident_role';w=json.loads((D/'window.json').read_text());rows=[]
for r in w:
 old=json.loads((CACHE/'grok'/(r['cache_key']+'.json')).read_text());text=(OUT/'content'/(r['hash']+'.txt')).read_text(encoding='utf-8-sig');safe,_=sanitize(text)
 if not r['failed']:rows.append({'path':r['path'],'result':'previously valid'});continue
 try:
  parsed=validate_output(r['diagnostic']['raw_output'],safe)
  result={**old,**parsed.model_dump(),'status':'validated','evidence_references':json.loads(r['diagnostic']['raw_output'])['evidence'],'complete_input':True,'offline_revalidation':{'rule':'source-matched declaration syntax support','original_cache_key':r['cache_key']},'validator_version':'source-reference-v3-declaration-repair'}
  write_json(CACHE/'offline_revalidated'/(r['cache_key']+'.json'),result,immutable=True);rows.append({'repo':r['repo'],'pr':r['pr'],'path':r['path'],'result':'recovered offline'})
 except ValueError as exc:rows.append({'repo':r['repo'],'pr':r['pr'],'path':r['path'],'result':'unknown','reason':str(exc)})
write_json(D/'revalidation.json',rows);protect_prior();print(json.dumps(rows,indent=2))
