import json,base64
from common import CACHE,OUT,sha256,write_json
from storage import Store,git_blob_sha,metadata_request
D=OUT/'full_cohort/incident_integrity';D.mkdir(exist_ok=True)
paths=list((OUT/'full_cohort').glob('*.json'))+list((OUT/'full_cohort').glob('*.csv'))+list((OUT/'full_cohort/batch_0006').rglob('*.csv'))
write_json(D/'preserved.json',{str(p):sha256(p.read_bytes()) for p in paths if p.is_file()})
r=json.loads((CACHE/'github/c70e898a15f7c2569c64a78c.json').read_text());a=r['request']['args'];d=r['data'];raw=base64.b64decode(d['content']);s=Store();prs=[]
for p in (CACHE/'github').glob('*.json'):
 x=json.loads(p.read_text())
 if x['request']['kind']=='metadata' and x.get('data',{}).get('head_sha')==a['ref'] and x['request']['args'].get('repository_full_name')==a['repository_full_name']:prs.append(x['request']['args']['pr_number'])
files,complete,_,_=s.files(a['repository_full_name'],prs[0]);expected=next(f for f in files if f['filename']==a['path'])
print(json.dumps({'request':r['request'],'prs':prs,'expected_file_metadata':expected,'content_fields':{k:v for k,v in d.items() if k!='content'},'decoded_bytes':len(raw),'computed_git_blob':git_blob_sha(raw),'decoded_hash_sha256':sha256(raw),'body_preview':raw[:150].decode(errors='replace')},indent=2))
write_json(D/'diagnosis.json',{'request':r['request'],'prs':prs,'expected_file_metadata':expected,'content_fields':{k:v for k,v in d.items() if k!='content'},'decoded_bytes':len(raw),'computed_git_blob':git_blob_sha(raw),'decoded_hash_sha256':sha256(raw)})
