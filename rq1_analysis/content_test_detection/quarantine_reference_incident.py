import json,base64
from common import CACHE,OUT,write_json,sha256
from storage import git_blob_sha
reqid='c70e898a15f7c2569c64a78c';r=json.loads((CACHE/'github'/(reqid+'.json')).read_text());raw=base64.b64decode(r['data']['content']);target='../../../Vendor/secp256k1/src/tests.c';assert git_blob_sha(target.encode())==r['data']['sha']=='c0ee7781b807c6adbbc00d26a0d761d36ae7d812'
D=OUT/'full_cohort/incident_integrity'
write_json(D/'confirmed_reference.json',{'request':r['request'],'pr_number':945,'expected_blob_sha':r['data']['sha'],'returned_metadata_sha':r['data']['sha'],'computed_response_blob_sha':git_blob_sha(raw),'response_sha256':sha256(raw),'expected_reference_text':target,'expected_reference_git_blob_sha':git_blob_sha(target.encode()),'finding':'Contents response returns target bytes while reporting link-path blob identity; Git mode unavailable offline. Target bytes not accepted.','classification':'unresolved'},immutable=True)
proof=CACHE/'quarantined_path_references';proof.mkdir(exist_ok=True)
write_json(proof/(reqid+'.json'),json.loads((D/'confirmed_reference.json').read_text()),immutable=True)
print('Hash-proven reference quarantine recorded; no source content accepted')
