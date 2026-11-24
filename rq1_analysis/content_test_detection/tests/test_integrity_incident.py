import json,base64
import pytest
from common import CACHE,OUT
from storage import Store,git_blob_sha,content_request

REPO='21-DOT-DEV/swift-secp256k1';HEAD='7db2793e98ee1abc4281809591793f29d8aea3e2';PATH='Projects/Sources/libsecp256k1Tests/tests.c';SHA='c0ee7781b807c6adbbc00d26a0d761d36ae7d812'

def test_actual_response_is_never_accepted_as_source():
 text,proof,pending=Store().content(REPO,HEAD,PATH,SHA)
 assert text is None and pending is None
 assert proof['status']=='quarantined_path_reference_contents_response'
 assert proof['actual_blob_sha']=='52614401c0a4080e44ae66082bde3422f800be01'
 assert git_blob_sha(b'../../../Vendor/secp256k1/src/tests.c')==SHA

def test_same_mismatch_without_investigated_proof_still_hard_fails(tmp_path,monkeypatch):
 import storage
 req=content_request(REPO,HEAD,PATH);original=(CACHE/'github'/(req['id']+'.json')).read_bytes()
 (tmp_path/'github').mkdir();(tmp_path/'github'/(req['id']+'.json')).write_bytes(original)
 monkeypatch.setattr(storage,'CACHE',tmp_path)
 text,proof,_=Store().content(REPO,HEAD,PATH,SHA)
 assert text is None and proof['integrity_error']

def test_quarantine_proof_cannot_cover_different_response(tmp_path,monkeypatch):
 import storage
 req=content_request(REPO,HEAD,PATH);(tmp_path/'github').mkdir();(tmp_path/'quarantined_path_references').mkdir()
 data=json.loads((CACHE/'github'/(req['id']+'.json')).read_text());data['data']['content']=base64.b64encode(b'changed bytes').decode()
 (tmp_path/'github'/(req['id']+'.json')).write_text(json.dumps(data))
 (tmp_path/'quarantined_path_references'/(req['id']+'.json')).write_bytes((CACHE/'quarantined_path_references'/(req['id']+'.json')).read_bytes())
 monkeypatch.setattr(storage,'CACHE',tmp_path)
 with pytest.raises(AssertionError):Store().content(REPO,HEAD,PATH,SHA)
