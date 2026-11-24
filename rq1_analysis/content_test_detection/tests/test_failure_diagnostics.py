import json
import pytest
import grok
from test_grok import resolver,GOOD,SOURCE

@pytest.mark.parametrize('case,output,finish,stage',[
 ('notification_html','{bad','REASON_STOP','schema_or_evidence'),
 ('prerequisites',json.dumps({**GOOD,'has_executable_tests':False}),'REASON_STOP','schema_or_evidence'),
 ('preprocessors',json.dumps({**GOOD,'evidence':[] }),'REASON_STOP','schema_or_evidence'),
 ('setup_plan',json.dumps({**GOOD,'evidence':['invented_symbol']}),'REASON_STOP','schema_or_evidence'),
 ('powershell',json.dumps(GOOD),'REASON_MAX_LEN','finish_reason')])
def test_failure_diagnostics_preserve_replayable_output(tmp_path,monkeypatch,case,output,finish,stage):
    # Synthetic regressions for lost-diagnostic mechanisms, not reconstructions
    # of the discarded provider responses named by these five cases.
    calls=[]
    def fake(*args):calls.append(1);return output,{'total_tokens':2},.001,finish
    r=resolver(tmp_path,monkeypatch,fake)
    got=r.resolve(SOURCE,'a.js','javascript',case)
    assert got['classification']=='uncertain'
    assert got['diagnostic']['stage']==stage
    assert got['diagnostic']['raw_output']==output
    assert r.resolve(SOURCE,'a.js','javascript',case)['cache_hit']
    assert len(calls)==1

def test_explicit_repair_limit_does_not_open_scaling_gate(tmp_path):
    b=grok.Budget(tmp_path/'budget.json',max_requests=100,repair_batch=True)
    for i in range(20):b.reserve(.06,str(i))
    with pytest.raises(RuntimeError,match='request_limit'):b.reserve(.06,'overflow')
    assert not b.state['smoke_validated']
