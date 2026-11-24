from types import SimpleNamespace
import pytest
import github_http as h

@pytest.mark.parametrize('statuses',[[500,200],[502,503,200]])
def test_transient_server_error_recovers_bounded(tmp_path,monkeypatch,statuses):
 calls=[];delays=[]
 def get(*a,**k):
  status=statuses[len(calls)];calls.append(status);return SimpleNamespace(status_code=status,headers={})
 monkeypatch.setattr(h.time,'sleep',lambda s:delays.append(s))
 result=h.get_with_retry(SimpleNamespace(get=get),'https://api.github.com/repos/unit/repo/pulls/119/files',{'id':'unit'},tmp_path,10)
 assert result.status_code==200 and len(calls)==len(statuses)
 assert h.read_count(tmp_path)==len(statuses)-1 and max(delays)<=2

def test_persistent_error_stops_after_three_and_does_not_fake_content(tmp_path,monkeypatch):
 calls=[];monkeypatch.setattr(h.time,'sleep',lambda *a:None)
 def get(*a,**k):calls.append(1);return SimpleNamespace(status_code=500,headers={})
 with pytest.raises(RuntimeError,match='after_3'):h.get_with_retry(SimpleNamespace(get=get),'url',{'id':'unit'},tmp_path,10)
 assert len(calls)==3 and h.read_count(tmp_path)==3

def test_transient_retries_cannot_cross_cumulative_read_cap(tmp_path,monkeypatch):
 monkeypatch.setattr(h.time,'sleep',lambda *a:None);calls=[]
 def get(*a,**k):calls.append(1);return SimpleNamespace(status_code=503,headers={})
 with pytest.raises(RuntimeError,match='request_limit'):h.get_with_retry(SimpleNamespace(get=get),'url',{'id':'unit'},tmp_path,1)
 assert len(calls)==1

@pytest.mark.parametrize('status',[401,403,404,429])
def test_auth_rate_and_missing_responses_not_retried(tmp_path,status):
 calls=[]
 def get(*a,**k):calls.append(1);return SimpleNamespace(status_code=status,headers={})
 assert h.get_with_retry(SimpleNamespace(get=get),'url',{},tmp_path,10).status_code==status
 assert len(calls)==1
