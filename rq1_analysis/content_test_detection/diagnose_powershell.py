import json,csv
from common import CACHE,OUT,HIST,sha256,write_json
from grok import validate_output
p=CACHE/'repair_smoke/grok/8a2c0f33d26884231ce69788f32f729cc08d65786244afc2049ac49e2a3ebf61.json'
r=json.loads(p.read_text());parsed=json.loads(r['diagnostic']['raw_output'])
text=None
for root in [HIST/'outputs/content',OUT/'content']:
    for f in root.rglob('*'):
        if f.is_file() and sha256(f.read_bytes())==r['content_sha256']:text=f.read_bytes().decode('utf-8-sig')
assert text is not None
citations=[{'citation':e,'length':len(e),'verbatim_present':e in text,'length_valid':3<=len(e)<=240} for e in parsed['evidence']]
write_json(OUT/'scale100/powershell_failure_diagnosis.json',{'classification_attempted':parsed['classification'],'finish_reason':r['diagnostic']['finish_reason'],'failure':'Unsupported evidence citation','citations':citations,'conclusion':'Exact-source citation failure; keep unknown. No citation rewriting or evidence deletion to force acceptance.'})
print(json.dumps(citations,indent=2))
