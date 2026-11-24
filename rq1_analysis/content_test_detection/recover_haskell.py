"""Recover exact archived Haskell citations rejected only by legacy length cap."""
import json
from common import CACHE,OUT,sha256,write_json,protect_prior
from grok import validate_output
D=OUT/'scale100/incident_haskell';diagnosis=json.loads((D/'diagnosis.json').read_text());recovered=[]
(CACHE/'offline_revalidated').mkdir(exist_ok=True)
for case in diagnosis['failures']:
    old=json.loads((CACHE/'grok'/(case['response_key']+'.json')).read_text())
    raw=(OUT/'content'/(old['content_sha256']+'.txt')).read_bytes();assert sha256(raw)==old['content_sha256']
    text=raw.decode('utf-8-sig');diag=old['diagnostic'];assert diag['finish_reason']=='REASON_STOP' and diag['complete_input']
    parsed=validate_output(diag['raw_output'],text)
    assert all(e in text for e in parsed.evidence)
    assert all(token in text for token in ['spec :: Spec','describe','it ','shouldBe'])
    result={**old,**parsed.model_dump(),'status':'validated','complete_input':True,'usage':diag['usage'],'reported_cost_usd':diag['reported_cost_usd'],'finish_reason':diag['finish_reason'],'offline_revalidation':{'rule':'legacy citation-length cap removed; exact source matching retained','original_cache_key':case['response_key'],'original_response_unchanged':True,'independent_human_reference':False}}
    write_json(CACHE/'offline_revalidated'/(case['response_key']+'.json'),result,immutable=True)
    recovered.append({'repo':case['repo'],'pr':case['pr'],'path':case['path'],'classification':parsed.classification,'offline_recovered':True})
write_json(D/'offline_recovery.json',recovered);protect_prior();print(json.dumps(recovered,indent=2))
