import json
import pytest
import grok,scale100 as s
from common import CACHE,OUT,sha256

def test_actual_cpp_rejection_and_no_paid_replay():
    r=json.loads((CACHE/'grok/31ea0bc9dfdc144465e74d78cd0a959a1485b39a912a7d2208444d10f4fb930a.json').read_text())
    raw=(OUT/'content'/(r['content_sha256']+'.txt')).read_bytes()
    assert sha256(raw)==r['content_sha256']
    text=raw.decode('utf-8-sig')
    value=json.loads(r['diagnostic']['raw_output'])
    assert sum(e not in text for e in value['evidence'])==1
    with pytest.raises(ValueError,match='Unsupported evidence'):grok.validate_output(value,text)
    resolver=s.Resolver(transport=lambda *a:pytest.fail('Paid call made'))
    got=resolver.resolve(text,'test/cpp/test_batch_builder.cpp','cpp',r['content_sha256'])
    assert got['cache_hit'] and got['has_executable_tests'] is None


def test_known_file_failure_continues_but_systematic_failure_stops(tmp_path,monkeypatch):
    monkeypatch.setattr(s,'CACHE',tmp_path)
    monkeypatch.setattr(grok.GrokResolver,'resolve',lambda *a,**k:{'status':'provider_or_validation_failure','error_type':'ValueError','diagnostic':{'stage':'schema_or_evidence'}})
    resolver=s.Resolver(budget=grok.Budget(tmp_path/'ledger.json'))
    resolver.current_repo='one-repository'
    assert resolver.resolve('source','a.cpp','cpp','one')['status']=='provider_or_validation_failure'
    for i in range(8):
        resolver.current_repo='one-repository'
        resolver.current_pr=i
        assert resolver.resolve('source','b.cpp','cpp',str(i))['status']=='provider_or_validation_failure'
    # Correlated file failures do not independently establish provider failure.
    resolver.current_repo='second-repository'
    assert resolver.resolve('source','b.cpp','cpp','nine')['status']=='provider_or_validation_failure'
    resolver.current_repo='third-repository'
    with pytest.raises(RuntimeError,match='systematic'):resolver.resolve('source','c.cpp','cpp','ten')

@pytest.mark.parametrize('status',['request_limit','spending_limit','invalid_cached_prediction'])
def test_limits_and_integrity_still_stop(tmp_path,monkeypatch,status):
    monkeypatch.setattr(s,'CACHE',tmp_path)
    monkeypatch.setattr(grok.GrokResolver,'resolve',lambda *a,**k:{'status':status})
    resolver=s.Resolver(budget=grok.Budget(tmp_path/'ledger.json'))
    with pytest.raises(RuntimeError,match='stopped_'):resolver.resolve('source','a.cpp','cpp','one')
