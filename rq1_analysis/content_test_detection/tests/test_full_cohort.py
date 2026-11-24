import json
import pandas as pd
import pytest
import full_cohort as f
from common import OUT,KEY,sha256

def test_fixed_500_is_proportional_unique_and_previously_unknown():
 d=pd.read_csv(f.DEST/'batch_0001/sample.csv');e=pd.read_csv(f.DEST/'entry_cohort.csv')
 assert len(d)==500 and not d.duplicated(KEY).any()
 assert d[KEY].merge(e,on=KEY,validate='one_to_one').test_added_content_verified.isna().all()
 assert d.repo_name.nunique()==140
 assert d.groupby('stratum').size().eq(d.groupby('stratum').allocated_batch_n.first()).all()
 assert (d.batch_inclusion_fraction>0).all()


def test_draw_resume_is_immutable():
 path=f.DEST/'batch_0001/sample.csv';before=path.read_bytes()
 entry=pd.read_csv(f.DEST/'entry_cohort.csv');_,again=f.make_queue(entry)
 assert len(again)==500 and path.read_bytes()==before

@pytest.mark.parametrize('label,live,retry,expected',[(1,True,False,False),(0,True,True,False),(None,True,False,True),(None,False,False,False),(None,False,True,True)])
def test_checkpoint_resume_does_not_skip_offline_unknowns(tmp_path,label,live,retry,expected):
 path=tmp_path/'checkpoint.csv';pd.DataFrame([{'test_added_content_verified':label}]).to_csv(path,index=False)
 assert f.needs_processing(path,live,retry)==expected


def test_published_unknowns_not_negative_and_resolved_baseline_unchanged():
 entry=pd.read_csv(f.DEST/'entry_cohort.csv');current=pd.read_csv(f.DEST/'current_main_outcomes.csv')
 known=entry[entry.test_added_content_verified.notna()]
 joined=known[KEY+['test_added_content_verified']].merge(current,on=KEY,suffixes=('_old',''),validate='one_to_one')
 corrections=f.DEST/'known_negative_corrections.json'
 if corrections.exists():
  for correction in json.loads(corrections.read_text()):
   mask=joined.repo_name.eq(correction['repo_name'])&joined.pr_number.eq(correction['pr_number'])
   joined.loc[mask,'test_added_content_verified_old']=correction['test_added_content_verified']
 assert joined.test_added_content_verified_old.eq(joined.test_added_content_verified).all()
 assert len(current)==3186


def test_prior_100pr_outputs_preserved():
 manifest=json.loads((f.DEST/'protected_100pr_outputs.json').read_text())
 assert all(sha256((OUT/path).read_bytes())==digest for path,digest in manifest.items())

def test_later_batch_is_disjoint_and_initial_queue_not_rewritten(tmp_path,monkeypatch):
 entry=pd.read_csv(f.DEST/'entry_cohort.csv');prior=pd.read_csv(f.DEST/'batch_0001/sample.csv')
 monkeypatch.setattr(f,'DEST',tmp_path);monkeypatch.setattr(f,'BATCH','batch_0002')
 (tmp_path/'batch_0001').mkdir();prior.to_csv(tmp_path/'batch_0001/sample.csv',index=False)
 _,second=f.make_queue(entry,n=20)
 assert len(second)==20
 assert not set(map(tuple,prior[KEY].to_numpy())) & set(map(tuple,second[KEY].to_numpy()))
 before=(tmp_path/'unresolved_queue.csv').read_bytes()
 f.make_queue(entry,n=20)
 assert (tmp_path/'unresolved_queue.csv').read_bytes()==before

def test_missing_repositories_stay_unknown_and_are_not_retrieved_repeatedly(tmp_path,monkeypatch):
 import scale100 as e,storage
 dest=tmp_path/'outputs';(dest/'checkpoints').mkdir(parents=True)
 cache=tmp_path/'cache';(cache/'github').mkdir(parents=True)
 monkeypatch.setattr(e,'DEST',dest);monkeypatch.setattr(e,'CACHE',cache);monkeypatch.setattr(storage,'CACHE',cache)
 calls=[]
 class Response:
  status_code=404;ok=False;headers={}
 class Session:
  def __init__(self):self.headers={}
  def get(self,*args,**kwargs):calls.append(1);return Response()
 monkeypatch.setattr(e.requests,'Session',Session)
 frame=pd.DataFrame([{'repo_name':'unit/missing','pr_number':1,'tool':'openspec','test_added':0},{'repo_name':'unit/missing','pr_number':2,'tool':'speckit','test_added':1}])
 groups={('unit/missing',n):pd.DataFrame([{'file_path':'src/a.py','change_status':'added'}]) for n in [1,2]}
 d,_,_=e.run_rows(frame,object(),True,1500,groups,allow_missing_resources=True)
 assert d.test_added_content_verified.isna().all() and len(calls)==2
 e.run_rows(frame,object(),True,1500,groups,allow_missing_resources=True)
 assert len(calls)==2

def test_frozen_selection_integrity_rejects_changes(tmp_path,monkeypatch):
 monkeypatch.setattr(f,'DEST',tmp_path);monkeypatch.setattr(f,'BATCH','batch_0001')
 (tmp_path/'batch_0001').mkdir();(tmp_path/'inputs').mkdir()
 (tmp_path/'batch_0001/sample.csv').write_text('repo_name,pr_number\na/b,1\n')
 (tmp_path/'unresolved_queue.csv').write_text('repo_name,pr_number\na/b,1\n')
 f.protect_selection();f.protect_selection()
 (tmp_path/'batch_0001/sample.csv').write_text('repo_name,pr_number\na/b,2\n')
 with pytest.raises(RuntimeError,match='integrity mismatch'):f.protect_selection()

@pytest.mark.parametrize('pause_at_content',[False,True])
def test_nonfile_reference_is_cached_unknown_not_negative(tmp_path,monkeypatch,pause_at_content):
 import scale100 as e,storage
 from github_http import GitHubLowQuota
 dest=tmp_path/'outputs';(dest/'checkpoints').mkdir(parents=True)
 cache=tmp_path/'cache';(cache/'github').mkdir(parents=True)
 monkeypatch.setattr(e,'DEST',dest);monkeypatch.setattr(e,'CACHE',cache);monkeypatch.setattr(storage,'CACHE',cache)
 calls=[]
 class Response:
  status_code=200;ok=True;headers={}
  def __init__(self,data,headers=None):self.data=data;self.headers=headers or {}
  def json(self):return self.data
 class Session:
  def __init__(self):self.headers={}
  def get(self,url,**kwargs):
   calls.append(url)
   if '/contents/' in url:
    headers={'X-RateLimit-Remaining':'10','X-RateLimit-Reset':'1234'} if pause_at_content else {}
    return Response({'type':'submodule','sha':'b'*40},headers)
   if '/files?' in url:return Response([{'filename':'ref/submodule','status':'added','sha':'b'*40}])
   return Response({'head':{'sha':'a'*40,'repo':None},'base':{'sha':'c'*40},'changed_files':1})
 monkeypatch.setattr(e.requests,'Session',Session);monkeypatch.setattr(e.time,'sleep',lambda *a:None)
 frame=pd.DataFrame([{'repo_name':'unit/nonfile','pr_number':1,'tool':'openspec','test_added':0}])
 groups={('unit/nonfile',1):pd.DataFrame([{'file_path':'ref/submodule','change_status':'added'}])}
 if pause_at_content:
  with pytest.raises(GitHubLowQuota):
   e.run_rows(frame,object(),True,1500,groups,allow_missing_resources=True)
  assert len(calls)==3
  assert len(list((cache/'github').glob('*.json')))==3
 d,a,_=e.run_rows(frame,object(),True,1500,groups,allow_missing_resources=True)
 assert d.test_added_content_verified.isna().all() and len(calls)==3
 assert a.retrieval_status.eq('submodule_commit_not_source_blob').all()
 e.run_rows(frame,object(),True,1500,groups,allow_missing_resources=True)
 assert len(calls)==3
