import json
from types import SimpleNamespace
import pandas as pd
import pytest
import overnight as n,full_cohort as f
from common import OUT,KEY


def test_hard_model_caps_and_missing_key(monkeypatch):
 monkeypatch.setenv('XAI_API_KEY','unit-test-not-sent')
 assert n.mode_allowed([{'charged_or_reserved_usd':.001}]*74)
 assert not n.mode_allowed([{'charged_or_reserved_usd':.001}]*100)
 assert not n.mode_allowed([{'charged_or_reserved_usd':3}])
 monkeypatch.delenv('XAI_API_KEY');assert not n.mode_allowed([])

def test_low_cost_order_keeps_selection_and_prioritizes_cached_work():
 sample=pd.DataFrame([{'repo_name':'r','pr_number':i,'execution_rank':i,'n_files':5} for i in [1,2,3]])
 states=pd.DataFrame([{'repo_name':'r','pr_number':1,'verification_state':'not_yet_examined','details':'[]'},{'repo_name':'r','pr_number':2,'verification_state':'waiting_grok_classification','details':'[]'},{'repo_name':'r','pr_number':3,'verification_state':'cache_ready_for_replay','details':'[]'}])
 before=sample.copy();order=f.prioritize_remaining(sample,states)
 assert list(order.pr_number)==[3,2,1];pd.testing.assert_frame_equal(before,sample)

def test_supervisor_modes_use_supported_flags_only():
 paid=n.child_command(1,7500,True);free=n.child_command(1,7500,False)
 assert '--live' in paid and '--deterministic-only' in free and '--prioritize-low-cost' in paid
 assert paid[paid.index('--max-grok-requests')+1]=='100'

def test_quota_handling_is_bounded(tmp_path,monkeypatch):
 class Response:
  status_code=200
  def json(self):return {'resources':{'core':{'remaining':0,'limit':5000,'reset':101}}}
 assert not n.quota(SimpleNamespace(get=lambda *a,**k:Response()))['allowed']
 monkeypatch.setattr(n.time,'time',lambda:100);calls=[];monkeypatch.setattr(n.time,'sleep',lambda s:calls.append(s))
 state={};assert n.wait_for_quota({'remaining':0,'reset_epoch':101},state,tmp_path,True)
 assert sum(calls)==6
 assert not n.wait_for_quota({'remaining':0,'reset_epoch':5000},state,tmp_path,True)


def test_prepared_second_batch_is_disjoint_and_preserves_first():
 a=pd.read_csv(OUT/'full_cohort/batch_0001/sample.csv');b=pd.read_csv(OUT/'full_cohort/batch_0002/sample.csv')
 assert len(b)==500 and not set(map(tuple,a[KEY].to_numpy())) & set(map(tuple,b[KEY].to_numpy()))


def test_missing_token_stops_before_network(tmp_path,monkeypatch):
 monkeypatch.setattr(n,'ROOT',tmp_path);(tmp_path/'progress.json').write_text(json.dumps({'main':{'positive':1,'negative':1,'unknown':1}}))
 monkeypatch.delenv('GITHUB_TOKEN',raising=False);monkeypatch.setattr(n.sys,'argv',['overnight.py','--live'])
 monkeypatch.setattr(n.requests,'Session',lambda:pytest.fail('Network client created'))
 n.main()
 state=json.loads(next(tmp_path.glob('overnight_runs/*/state.json')).read_text());assert state['stop_reason']=='missing_GITHUB_TOKEN'

@pytest.mark.parametrize('returncode,attempt_count,expected_passes,quota_pause',[
 (0,74,2,False),(1,74,1,False),(0,100,2,False),(0,74,2,True),
])
def test_supervisor_continues_batches_but_stops_provider_errors(tmp_path,monkeypatch,returncode,attempt_count,expected_passes,quota_pause):
 monkeypatch.setattr(n,'CACHE',tmp_path/'isolated_cache')
 monkeypatch.setattr(n,'ROOT',tmp_path);monkeypatch.setattr(n,'protect_prior',lambda:None)
 (tmp_path/'progress.json').write_text(json.dumps({'main':{'positive':1,'negative':1,'unknown':2},'batch':{'pending_actionable':1},'model_quality_fallback':True}))
 for number in [1,2]:
  directory=tmp_path/f'batch_{number:04d}';directory.mkdir();(directory/'sample.csv').write_text('repo_name,pr_number\na/b,1\n')
 monkeypatch.setenv('GITHUB_TOKEN','unit-not-sent');monkeypatch.setenv('XAI_API_KEY','unit-not-sent')
 monkeypatch.setattr(n,'ledger',lambda:[{'charged_or_reserved_usd':.001}]*attempt_count)
 class Response:
  status_code=200
  def json(self):return {'resources':{'core':{'remaining':5000,'limit':5000,'reset':9999999999}}}
 class Session:
  def __init__(self):self.headers={}
  def get(self,*a,**k):return Response()
 monkeypatch.setattr(n.requests,'Session',Session);monkeypatch.setattr(n.time,'sleep',lambda *a:None)
 commands=[]
 def child(command,**kwargs):
  commands.append(command)
  if returncode:(tmp_path/'stop_status.json').write_text(json.dumps({'reason':'unexpected_model_failure'}))
  if quota_pause and len(commands)==1:
   p=tmp_path/'progress.json';data=json.loads(p.read_text())
   data['execution']={'completion_status':'github_quota_paused'}
   p.write_text(json.dumps(data))
   (tmp_path/'stop_status.json').write_text(json.dumps({'reason':'github_low_quota'}))
  elif quota_pause:
   p=tmp_path/'progress.json';data=json.loads(p.read_text());data.pop('execution')
   p.write_text(json.dumps(data))
  return SimpleNamespace(returncode=returncode)
 monkeypatch.setattr(n.subprocess,'run',child);monkeypatch.setattr(n.sys,'argv',['overnight.py','--live','--max-passes','2'])
 n.main()
 assert len(commands)==expected_passes
 assert commands[0][commands[0].index('--batch-number')+1]=='1'
 if expected_passes==2:assert commands[1][commands[1].index('--batch-number')+1]==('1' if quota_pause else '2')
 if attempt_count==100:assert all('--deterministic-only' in c for c in commands)


@pytest.mark.parametrize('saved_block',[False,True])
def test_seven_batches_free_first_and_paid_round_robin_until_quality_stop(tmp_path, monkeypatch,saved_block):
    monkeypatch.setattr(n, 'ROOT', tmp_path)
    monkeypatch.setattr(n, 'CACHE', tmp_path / 'cache')
    monkeypatch.setattr(n, 'protect_prior', lambda: None)
    monkeypatch.setenv('GITHUB_TOKEN', 'offline-only')
    monkeypatch.setenv('XAI_API_KEY', 'offline-only')
    monkeypatch.setattr(n, 'quota', lambda _: {'allowed': True, 'remaining': 5000})
    monkeypatch.setattr(n, 'saved_quality_block', lambda: saved_block)
    monkeypatch.setattr(n.sys, 'argv', ['overnight.py', '--live', '--max-grok-spend', '7',
                                           '--max-grok-requests', '1000', '--max-new-model-calls', '5',
                                           '--github-limit', '13025', '--prioritize-low-cost'])
    ledger = [{'charged_or_reserved_usd': .04}] * 101
    monkeypatch.setattr(n, 'ledger', lambda: ledger)
    progress = {'main': {'positive': 1, 'negative': 1, 'unknown': 7},
                'batch': {'pending_actionable': 1},
                'verification_states': {'waiting_grok_classification': 1}}
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(progress))
    for b in range(1, 8):
        batch = tmp_path / f'batch_{b:04d}'
        batch.mkdir()
        (batch / 'sample.csv').write_text(f'repo_name,pr_number\na/b,{b}\n')
    commands = []

    def child(command, **_):
        commands.append(command)
        if '--live' in command:
            ledger.append({'charged_or_reserved_usd': .01})
        progress['model_quality_fallback'] = len(commands) == 16
        path.write_text(json.dumps(progress))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(n.subprocess, 'run', child)
    n.main()
    expected = list(range(1,8)) if saved_block else list(range(1, 8)) * 2 + [1, 2]
    assert [int(c[c.index('--batch-number') + 1]) for c in commands] == expected
    assert all('--deterministic-only' in c for c in commands[:7])
    assert all('--live' in c and '--fetch-github' not in c for c in commands[7:])
    for c in commands:
        for option, value in [('--max-grok-spend', '7.0'), ('--max-grok-requests', '1000'),
                              ('--max-new-model-calls', '5'), ('--github-limit', '13025')]:
            assert c[c.index(option) + 1] == value
        assert '--prioritize-low-cost' in c and '--rearm-model-quality' not in c
    state = json.loads(next(tmp_path.glob('overnight_runs/*/state.json')).read_text())
    assert state['stop_reason'] == 'model_quality_fallback'


def test_batch_priority_prefers_one_model_file_without_other_blockers(tmp_path,monkeypatch):
    monkeypatch.setattr(n,'ROOT',tmp_path)
    model={'model_status':'dry_run'}
    blocked={'retrieval':'symlink_not_followed'}
    for batch,details in [(1,[model,blocked]),(2,[model,model]),(3,[model])]:
        path=tmp_path/f'batch_{batch:04d}'
        path.mkdir()
        pd.DataFrame([{'verification_state':'waiting_grok_classification',
                       'details':json.dumps(details)}]).to_csv(path/'progress_states.csv',index=False)
    assert sorted([1,2,3],key=n.model_batch_priority)==[3,2,1]
