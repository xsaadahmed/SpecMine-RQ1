import json
import pytest
import grok,scale100 as e
from common import OUT,CACHE
from test_grok import GOOD,SOURCE
D=OUT/'full_cohort/incident_fallback'

@pytest.mark.parametrize('row',json.loads((D/'window.json').read_text()),ids=lambda r:r['path'])
def test_actual_fallback_window(row):
 if not row['failed']:return
 text=(OUT/'content'/(row['hash']+'.txt')).read_text(encoding='utf-8-sig');safe,_=grok.sanitize(text)
 if row['path'].endswith(('fedauth_strategy.cpp','sql_auth_strategy.cpp')):assert grok.validate_output(row['diagnostic']['raw_output'],safe).classification=='not_test'
 else:
  with pytest.raises(ValueError):grok.validate_output(row['diagnostic']['raw_output'],safe)

def test_quality_disables_new_calls_but_cached_valid_decisions_work(tmp_path,monkeypatch):
 monkeypatch.setattr(e,'CACHE',tmp_path);(tmp_path/'grok').mkdir()
 monkeypatch.setattr(e,'BASE',tmp_path/'base')
 calls=[]
 def fail(*a,**k):calls.append(1);return {'status':'provider_or_validation_failure','error_type':'ValueError','diagnostic':{'stage':'schema_or_evidence'}}
 monkeypatch.setattr(grok.GrokResolver,'resolve',fail)
 r=e.Resolver(fallback_on_quality=True,budget=grok.Budget(tmp_path/'ledger.json'))
 for i in range(10):
  r.current_repo='repo'+str(i%3);r.current_pr=i
  r.resolve('source','file.cpp','cpp',str(i))
 assert r.model_disabled and len(calls)==10
 assert r.resolve('source','other.cpp','cpp','new')['status']=='model_quality_fallback' and len(calls)==10
 record={**GOOD,'status':'validated','content_sha256':'goodhash','model':grok.MODEL,'reasoning_effort':grok.REASONING,'cache_key':'cached','prompt_version':grok.PROMPT_VERSION}
 (tmp_path/'grok/good.json').write_text(json.dumps(record))
 assert r.resolve(SOURCE,'a.js','javascript','goodhash')['cache_hit'] and len(calls)==10

def test_fallback_uncertain_file_cannot_make_negative():
 from pipeline import search_pr
 files=[{'filename':'tests/a.cpp','status':'added'},{'filename':'tests/b.cpp','status':'added'}]
 def fetch(f):return 'source',{'status':'verified'},None
 def classify(text,f,prov):return {'classification':'uncertain','has_executable_tests':None,'needs_review':True,'method':'deterministic'}
 assert search_pr(files,fetch,classify)[0]['test_added_content_verified'] is None
 def positive(text,f,prov):
  if f['filename'].endswith('b.cpp'):return {'classification':'automated_test','has_executable_tests':True,'needs_review':False,'method':'deterministic','evidence':['confirmed']}
  return classify(text,f,prov)
 assert search_pr(files,fetch,positive)[0]['test_added_content_verified']==1
