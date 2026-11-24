import base64,json
import pytest
from fetch_github import normalize,MAX_CONTENT_BYTES
from storage import Store,content_request,request,git_blob_sha
from common import write_json

def file(raw=b'assert True\n'):
 return {'type':'file','sha':git_blob_sha(raw),'size':len(raw),'content':base64.b64encode(raw).decode(),'encoding':'base64'}

@pytest.mark.parametrize('body,reason',[
 ([], 'directory_listing'),({'type':'dir'},'directory'),({'type':'symlink','target':'../../skills/example'},'symlink_not_followed'),({'type':'file','submodule_git_url':'https://example.com/repo'},'submodule_commit_not_source_blob'),({'message':'Not Found'},'api_error_object'),(None,'unexpected_response_type'),({},'missing_or_invalid_blob_sha')])
def test_content_variants_without_content(body,reason):
 assert normalize('content',body)['unavailable_reason']==reason

@pytest.mark.parametrize('change',[{'content':None},{'content':''},{'encoding':'none','content':''}])
def test_nonempty_metadata_never_becomes_empty_file(change):
 body=file();body.update(change)
 assert normalize('content',body)['unavailable_reason']=='blob_fallback_required'

def test_valid_base64_and_proven_empty_file():
 assert normalize('content',file())['content']
 assert normalize('content',file(b''))['content']==''
 body=file(b'');body.pop('content')
 assert normalize('content',body)['unavailable_reason']=='blob_fallback_required'

def test_local_size_limit_is_explicit():
 body=file();body['size']=MAX_CONTENT_BYTES+1
 assert normalize('content',body)['unavailable_reason']=='local_content_size_limit'

def test_pinned_blob_fallback_and_hash_verification(tmp_path,monkeypatch):
 import storage
 monkeypatch.setattr(storage,'CACHE',tmp_path);(tmp_path/'github').mkdir();monkeypatch.setattr(storage,'OUT',tmp_path)
 monkeypatch.setattr(storage,'ROOT',tmp_path.parent)
 (tmp_path/'content').mkdir()
 raw=b'def test_real():\n assert True\n';body=file(raw);head='a'*40;repo='unit/blob';path='tests/test_real.py'
 meta={**body,'encoding':'none','content':''};req=content_request(repo,head,path)
 write_json(tmp_path/'github'/(req['id']+'.json'),{'request':req,'ok':True,'data':normalize('content',meta)})
 store=Store();text,prov,pending=store.content(repo,head,path,body['sha']);assert text is None and pending['kind']=='blob' and pending['args']['ref']==head
 write_json(tmp_path/'github'/(pending['id']+'.json'),{'request':pending,'ok':True,'data':normalize('blob',body)})
 text,proof,_=Store().content(repo,head,path,body['sha']);assert text==raw.decode() and proof['commit_sha']==head
 bad={**body,'sha':'b'*40};write_json(tmp_path/'github'/(pending['id']+'.json'),{'request':pending,'ok':True,'data':normalize('blob',bad)})
 assert Store().content(repo,head,path,body['sha'])[1]['integrity_error']
