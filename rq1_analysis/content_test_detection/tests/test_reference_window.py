import json
import pytest
import grok,scale100 as s
from common import CACHE,OUT,sha256
from test_grok import GOOD
D=OUT/'scale100/incident_references'
ROWS=json.loads((D/'ten_decisions_revalidated.json').read_text())

@pytest.mark.parametrize('row',ROWS,ids=[r['path'].split('/')[-1] for r in ROWS])
def test_actual_ten_decision_window(row):
 old=json.loads((CACHE/'grok'/(row['key']+'.json')).read_text());raw=(OUT/'content'/(row['hash']+'.txt')).read_bytes();assert sha256(raw)==row['hash']
 text=raw.decode('utf-8-sig');safe,_=grok.sanitize(text)
 if old['status']=='validated':grok.validate_cached_classification(old,text);return
 if row['recovered_offline']:
  parsed=grok.validate_output(old['diagnostic']['raw_output'],safe)
  assert parsed.classification==row['classification']
  recovered=json.loads((CACHE/'offline_revalidated'/(row['key']+'.json')).read_text())
  grok.validate_cached_classification(recovered,text)
 else:
  with pytest.raises(ValueError,match='absent on cited line'):grok.validate_output(old['diagnostic']['raw_output'],safe)

def test_structured_swift_reference_grounding_and_retrieved_lines():
 source='import Testing\n@Test\nfunc realTest() {\n defer { cleanup() }\n #expect(actual == expected)\n}'
 value={**GOOD,'language':'Swift','evidence':[{'line':2,'symbol':'Test','role':'registration'},{'line':5,'symbol':'expect','role':'assertion'}]}
 assert grok.validate_output(value,source).evidence==['Test','expect']
 assert grok.resolve_source_lines(value['evidence'],source)[1]['text']==' #expect(actual == expected)'
 for refs in [[{'line':1,'symbol':'Test','role':'registration'},{'line':5,'symbol':'expect','role':'assertion'}],[{'line':2,'symbol':'Test','role':'registration'},{'line':5,'symbol':'fabricated','role':'assertion'}]]:
  with pytest.raises(ValueError):grok.validate_output({**value,'evidence':refs},source)

def test_irrelevant_swift_symbol_does_not_prove_test():
 source='func production() {\n let value = 1\n return value\n}'
 value={**GOOD,'language':'Swift','evidence':[{'line':1,'symbol':'production','role':'declaration'},{'line':3,'symbol':'value','role':'code'}]}
 with pytest.raises(ValueError,match='Swift positive lacks'):grok.validate_output(value,source)

def test_unexpected_provider_failure_still_stops(tmp_path,monkeypatch):
 monkeypatch.setattr(s,'CACHE',tmp_path)
 monkeypatch.setattr(grok.GrokResolver,'resolve',lambda *a,**k:{'status':'provider_or_validation_failure','error_type':'RpcError','diagnostic':{'stage':'transport'}})
 resolver=s.Resolver(budget=grok.Budget(tmp_path/'ledger.json'))
 with pytest.raises(RuntimeError,match='unexpected_model_failure'):resolver.resolve('source','test.swift','swift','newhash')
