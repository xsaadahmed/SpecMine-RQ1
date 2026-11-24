import base64
import hashlib

import extract
from hv_common import content_req


def test_git_blob_hash_has_independent_known_value():
    assert extract.git_blob_sha(b"hello\n")=="ce013625030ba8dba906f756967f9e9ca394464a"


def test_unpinned_branch_is_rejected():
    import pytest
    with pytest.raises(AssertionError):content_req('a/b','main','spec.md')


def test_success_requires_both_response_and_diff_blob_hash(monkeypatch,tmp_path):
    raw=b"## Acceptance Criteria\n- Works\n"
    blob=extract.git_blob_sha(raw)
    response={'ok':True,'data':{'encoding':'base64','content':base64.b64encode(raw).decode(),'sha':blob},'retrieved_at':'2026-11-02T00:00:00Z'}
    monkeypatch.setattr(extract,'cached',lambda req:response)
    monkeypatch.setattr(extract,'OUT',tmp_path)
    (tmp_path/'content').mkdir()
    req={'id':'known'}
    result,text=extract.verified_content(req,blob)
    assert result['retrieval_status']=='verified' and text.startswith('## Acceptance')
    assert result['content_sha256']==hashlib.sha256(raw).hexdigest()
    result,text=extract.verified_content(req,'0'*40)
    assert result['retrieval_status']=='verification_failed' and text is None


def test_fetch_failure_never_becomes_absent_feature(monkeypatch):
    monkeypatch.setattr(extract,'cached',lambda req:{'ok':False,'detail':'404'})
    result,text=extract.verified_content({'id':'missing'})
    assert result['retrieval_status']=='remote_error' and text is None
