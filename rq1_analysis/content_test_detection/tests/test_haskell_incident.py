import json
import pytest
import grok,scale100 as s
from common import CACHE,OUT,sha256
from test_grok import GOOD

@pytest.mark.parametrize('key',[
'66a083a216e0e987aa5d3d58cbc04bf51f68bb810a78a189297e7556d4cf7a3b',
'78f7f3160a62857449d471bf1f016fa238c9ec756bc2b3fa4cced0ce31e3e2cb',
'0a465c4021aa525a3680c3bb3d8a072bfad05d17ff8373f6829b2054aae7f4a6'])
def test_exact_archived_haskell_recovered_without_paid_calls(key):
    old=json.loads((CACHE/'grok'/(key+'.json')).read_text())
    raw=(OUT/'content'/(old['content_sha256']+'.txt')).read_bytes()
    assert sha256(raw)==old['content_sha256']
    text=raw.decode('utf-8-sig');value=json.loads(old['diagnostic']['raw_output'])
    assert all(e in text for e in value['evidence']) and any(len(e)>240 for e in value['evidence'])
    assert grok.validate_output(value,text).classification=='automated_test'
    bad={**value,'evidence':[value['evidence'][0]+' invented text']}
    with pytest.raises(ValueError,match='Unsupported'):grok.validate_output(bad,text)
    resolver=s.Resolver(transport=lambda *a:pytest.fail('Paid call'))
    assert resolver.resolve(text,'test/StateSpec.hs','haskell',old['content_sha256'])['cache_hit']


def test_line_symbol_evidence_checks_actual_locations_and_code():
    source='function test_real() {\n  expect(1).toBe(1);\n}\n// invented\nconst text = "quoted_symbol";'
    good={**GOOD,'evidence':['L1:test_real','L2:expect']}
    parsed=grok.validate_output(good,source)
    assert parsed.evidence==['test_real','expect']
    for refs in [['L2:test_real','L1:expect'],['L1:test_real','L99:expect'],['L1:test_real','L4:invented'],['L1:test_real','L5:quoted_symbol'],['L1:test_real']]:
        with pytest.raises(ValueError):grok.validate_output({**good,'evidence':refs},source)


def test_cache_reference_revalidation_rejects_wrong_line():
    value={**GOOD,'evidence':['test_real','expect'],'evidence_references':['L1:test_real','L2:expect'],'complete_input':True}
    text='function test_real() {\n expect(1).toBe(1);\n}'
    assert grok.validate_cached_classification(value,text).has_executable_tests
    value['evidence_references']=['L1:expect','L2:test_real']
    with pytest.raises(ValueError):grok.validate_cached_classification(value,text)

def test_one_pr_degrades_to_static_analysis_instead_of_more_paid_calls(tmp_path,monkeypatch):
    monkeypatch.setattr(s,'CACHE',tmp_path)
    calls=[]
    def fake(*args,**kwargs):
        calls.append(1)
        return {'status':'provider_or_validation_failure','error_type':'ValueError','diagnostic':{'stage':'schema_or_evidence'}}
    monkeypatch.setattr(grok.GrokResolver,'resolve',fake)
    r=s.Resolver(budget=grok.Budget(tmp_path/'ledger.json'))
    r.current_repo='one';r.current_pr=1
    for i in range(3):r.resolve('code','a.hs','haskell',str(i))
    assert r.resolve('code','b.hs','haskell','next')['status']=='per_pr_model_deferred'
    assert len(calls)==3
    r.current_pr=2
    assert r.resolve('code','a.hs','haskell','other')['status']=='provider_or_validation_failure'
