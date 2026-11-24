import base64
import json
import storage


def test_corrupt_blob_remains_unknown(tmp_path):
    s=storage.Store();s.old=tmp_path/'old';s.new=tmp_path/'new';s.old.mkdir();s.new.mkdir()
    req=storage.content_request('a/b','a'*40,'test.py')
    raw=b'def test_x(): assert True'
    (s.new/(req['id']+'.json')).write_text(json.dumps({'request':req,'ok':True,'data':{'content':base64.b64encode(raw).decode(),'encoding':'base64','sha':'0'*40}}))
    text,meta,pending=s.content('a/b','a'*40,'test.py')
    assert text is None and meta['status']=='invalid_hash_encoding_or_binary' and pending is None


def test_unknown_commit_and_missing_pages_do_not_produce_empty_complete_list(tmp_path):
    s=storage.Store();s.old=tmp_path/'old';s.new=tmp_path/'new';s.old.mkdir();s.new.mkdir()
    assert s.files('a/b',1)[0] is None and not s.files('a/b',1)[1]
    req=storage.metadata_request('a/b',1)
    (s.new/(req['id']+'.json')).write_text(json.dumps({'request':req,'ok':True,'data':{'changed_files':1,'head_sha':'a'*40}}))
    rows,complete,pending,_=s.files('a/b',1)
    assert rows==[] and not complete and pending
