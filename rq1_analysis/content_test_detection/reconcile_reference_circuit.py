import json,csv
from common import OUT,write_json
from grok import WireClassification,VALIDATOR_VERSION
D=OUT/'scale100/incident_references';rows=json.loads((D/'ten_decisions_revalidated.json').read_text());window=[]
for r in rows:
 good=r['recovered_offline'] or r['status']=='validated'
 window.append({'failed':not good,'repo':r['repo'],'pr':r['pr'],'path':r['path'],'hash':r['hash'],'cache_key':r['key'],'status':'validated' if good else 'provider_or_validation_failure','finish':r['finish'],'prompt_version':r['prompt_version'],'validator_version':VALIDATOR_VERSION,'origin':'offline_revalidated_live_response','diagnostic':r['post_validation']})
p=OUT/'scale100/circuit_state_source-reference-v3.json'
if not p.exists():write_json(p,window,immutable=True)
write_json(D/'new_wire_schema.json',WireClassification.model_json_schema())
with (D/'ten_decisions.csv').open('w',encoding='utf-8',newline='') as f:
 fields=['repo','pr','path','live','status','finish','schema_passed','error','prompt_version','validator_version','recovered_offline','post_validation']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
print('Offline recovered',sum(r['recovered_offline'] for r in rows))
