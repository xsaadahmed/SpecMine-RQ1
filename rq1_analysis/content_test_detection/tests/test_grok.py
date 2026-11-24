import json
import pytest
import grok

SOURCE='function test_real() { expect(1).toBe(1); }'
GOOD={'classification':'automated_test','has_executable_tests':True,'language':'javascript','evidence':['test_real','expect(1).toBe(1)'],'reason':'Implemented assertion case','needs_review':False}


def resolver(tmp_path,monkeypatch,transport,dry=False,limit=10,spend=3):
    (tmp_path/'grok').mkdir(exist_ok=True)
    monkeypatch.setattr(grok,'CACHE',tmp_path)
    monkeypatch.setenv('XAI_API_KEY','unit-test-placeholder-never-sent')
    b=grok.Budget(tmp_path/'ledger.json',max_spend=spend,max_requests=limit)
    return grok.GrokResolver(dry_run=dry,transport=transport,budget=b)


def test_schema_flags_and_evidence_are_verified():
    assert grok.validate_output(GOOD,SOURCE).has_executable_tests
    for bad in [{**GOOD,'has_executable_tests':False},{**GOOD,'evidence':['invented_test']},{**GOOD,'extra':'field'}]:
        with pytest.raises(ValueError):grok.validate_output(bad,SOURCE)
    with pytest.raises(ValueError):grok.validate_output({**GOOD,'classification':'not_test','has_executable_tests':False},SOURCE,complete=False)


def test_cache_reuses_identical_content_without_a_second_charge(tmp_path,monkeypatch):
    calls=[]
    def fake(prompt,payload):calls.append(payload);return json.dumps(GOOD),{'prompt_tokens':30,'completion_tokens':30},.0001,'REASON_STOP'
    r=resolver(tmp_path,monkeypatch,fake)
    a=r.resolve(SOURCE,'a.js','javascript','samehash')
    b=r.resolve(SOURCE,'different.js','javascript','samehash')
    assert a['status']=='validated' and b['cache_hit'] and len(calls)==1
    assert len(r.budget.state['attempts'])==1


def test_dry_run_and_missing_key_never_invoke_transport(tmp_path,monkeypatch):
    def forbidden(*args):raise AssertionError('Paid transport invoked')
    r=resolver(tmp_path,monkeypatch,forbidden,dry=True)
    assert r.resolve(SOURCE,'a.js','javascript','one')['status']=='dry_run'
    r.dry_run=False;monkeypatch.delenv('XAI_API_KEY')
    assert r.resolve(SOURCE,'a.js','javascript','one')['status']=='missing_XAI_API_KEY'
    assert not r.budget.state['attempts']


def test_malformed_output_and_failed_citations_remain_unknown_and_cached(tmp_path,monkeypatch):
    calls=[]
    def bad(*args):calls.append(1);return '{bad json',{},None,'REASON_STOP'
    r=resolver(tmp_path,monkeypatch,bad)
    a=r.resolve(SOURCE,'a.js','javascript','hash')
    b=r.resolve(SOURCE,'a.js','javascript','hash')
    assert a['has_executable_tests'] is None and b['has_executable_tests'] is None and len(calls)==1
    assert r.budget.state['attempts'][0]['charged_or_reserved_usd']>=.06


def test_budget_is_persistent_and_fail_closed(tmp_path,monkeypatch):
    def fake(*args):return json.dumps(GOOD),{},.001,'REASON_STOP'
    r=resolver(tmp_path,monkeypatch,fake,limit=1)
    r.resolve(SOURCE,'a.js','javascript','one')
    assert r.resolve(SOURCE,'b.js','javascript','two')['status']=='request_limit'
    another=grok.Budget(tmp_path/'ledger.json',max_requests=1)
    with pytest.raises(RuntimeError):another.reserve(.06,'new')
    with pytest.raises(ValueError):grok.Budget(tmp_path/'other.json',max_spend=3.01)


def test_privacy_and_conflicts_do_not_force_predictions(tmp_path,monkeypatch):
    assert grok.sanitize('-----BEGIN ' 'PRIVATE KEY-----\nsecret')[0] is None
    assert grok.sanitize('XAI_API_KEY="xai-' 'abcdefghijklmnopqrstuvwxyz"')[0] is None
    clean,_=grok.sanitize('author@example.com')
    assert 'author@example.com' not in clean
    def fake(*args):return json.dumps(GOOD),{},.001,'REASON_STOP'
    r=resolver(tmp_path,monkeypatch,fake)
    out=r.resolve(SOURCE,'a.js','javascript','hash',strong={'classification':'not_test','has_executable_tests':False})
    assert out['has_executable_tests'] is None


def test_truncated_responses_are_not_accepted(tmp_path,monkeypatch):
    def fake(*args):return json.dumps(GOOD),{},.001,'REASON_MAX_LEN'
    r=resolver(tmp_path,monkeypatch,fake)
    assert r.resolve(SOURCE,'a.js','javascript','hash')['status']=='provider_or_validation_failure'


def test_rate_limits_have_bounded_counted_retries(tmp_path,monkeypatch):
    import grpc
    class RateLimit(grpc.RpcError):
        def code(self):return grpc.StatusCode.RESOURCE_EXHAUSTED
    calls=[]
    def fail(*args):calls.append(1);raise RateLimit()
    monkeypatch.setattr(grok.time,'sleep',lambda _:None)
    r=resolver(tmp_path,monkeypatch,fail)
    out=r.resolve(SOURCE,'a.js','javascript','hash')
    assert out['has_executable_tests'] is None and len(calls)==3
    assert len(r.budget.state['attempts'])==3
    assert sum(x['charged_or_reserved_usd'] for x in r.budget.state['attempts'])>=.18


def test_sdk_parameters_without_an_external_request(monkeypatch):
    import xai_sdk
    captured={}
    class Usage:
        prompt_tokens=10;completion_tokens=20;total_tokens=30;cost_in_usd_ticks=1000
        def HasField(self,name):return name=='cost_in_usd_ticks'
    class Response:
        content=json.dumps(GOOD);usage=Usage();finish_reason='REASON_STOP'
    class Chat:
        def create(self,**kwargs):captured.update(kwargs);return self
        def sample(self):return Response()
    class Client:
        def __init__(self,**kwargs):self.chat=Chat();captured['client']=kwargs
    monkeypatch.setattr(xai_sdk,'Client',Client)
    monkeypatch.setenv('XAI_API_KEY','unit-test-placeholder-never-sent')
    _,usage,cost,_=grok.sdk_call('instructions',SOURCE)
    assert captured['model']=='grok-4.3' and captured['reasoning_effort']=='none'
    assert captured['response_format'] is grok.WireClassification and captured['store_messages'] is False
    assert captured['client']['channel_options']==[('grpc.enable_retries',0)]
    assert usage['total_tokens']==30 and cost==1e-7


def test_cached_evidence_is_revalidated_without_charging_again(tmp_path,monkeypatch):
    calls=[]
    def fake(*args):calls.append(1);return json.dumps(GOOD),{},.001,'REASON_STOP'
    r=resolver(tmp_path,monkeypatch,fake)
    r.resolve(SOURCE,'a.js','javascript','hash')
    path=tmp_path/'grok'/(grok.cache_key('hash')+'.json')
    corrupted=json.loads(path.read_text());corrupted['evidence']=['invented_case'];path.write_text(json.dumps(corrupted))
    output=r.resolve(SOURCE,'a.js','javascript','hash')
    assert output['has_executable_tests'] is None and output['status']=='invalid_cached_prediction' and len(calls)==1
