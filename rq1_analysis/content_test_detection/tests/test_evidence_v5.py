import json
import sys

import pytest

import evidence_trial
import grok
import overnight
from common import OUT


def response(classification, refs):
    return {'classification':classification, 'language':'generic',
            'has_executable_tests':classification=='automated_test', 'needs_review':False,
            'evidence':[{'line':line,'symbol':name,'role':role} for line,name,role in refs],
            'reason':'Reviewed fixture'}


@pytest.mark.parametrize('index,refs', [
    (0, [(27,'formatAmount','declaration')]),
    (1, [(1,'JAVA_HOME','code')]),
    (2, [(113,'@Test','declaration'),(120,'assertThat','assertion')]),
])
def test_trial_fixture_is_reproducible_with_valid_evidence(index, refs):
    case = evidence_trial.CASES[index]
    source, _ = evidence_trial.source_for(case)
    value = response(case[4], refs)
    assert grok.validate_evidence_v5(value, source).classification == case[4]
    value['evidence'][0]['symbol'] = 'fabricated'
    with pytest.raises(ValueError):
        grok.validate_evidence_v5(value, source)


@pytest.mark.parametrize('source,name', [
    ('<!doctype html>','html'), ('let {','let'),
    ("import { page } from '$app/state';",'page'), ('enable-pre-post-scripts=true','enable-pre-post-scripts'),
    ('#!/usr/bin/env bash','bash'), ('{#if formatAmount(x)}','formatAmount'),
])
def test_role_relabel_does_not_rescue_ungrounded_references(source, name):
    for role in ['declaration','code']:
        with pytest.raises(ValueError):
            grok.validate_evidence_v5(response('not_test',[(1,name,role)]),source)


def test_trial_cannot_reserve_twice_or_dispatch_a_different_file(tmp_path,monkeypatch):
    budget = evidence_trial.TrialBudget(tmp_path/'ledger.json',max_spend=7,max_requests=1000)
    budget.allowed_key = 'planned'
    monkeypatch.setattr(evidence_trial.scale100.ScalingBudget,'reserve',
                        lambda self,bound,task:self.state['attempts'].append({'task':task}))
    with pytest.raises(RuntimeError,match='preflight'):
        budget.reserve(.06,'other')
    budget.reserve(.06,'planned')
    with pytest.raises(RuntimeError,match='preflight'):
        budget.reserve(.06,'planned')
    assert budget.state['attempts']==[{'task':'planned'}]


def test_overnight_permission_needs_every_verified_case(tmp_path,monkeypatch):
    assert not evidence_trial.approved(tmp_path, [])
    folder=tmp_path/evidence_trial.NAME
    folder.mkdir()
    expected=[{'repo_name':c[0],'pr_number':c[1],'outcome':int(c[4]=='automated_test')}
              for c in evidence_trial.CASES]
    (folder/'result.json').write_text(json.dumps({'passed':True,'outcomes':expected}))
    monkeypatch.setattr(evidence_trial,'verified_decision',lambda case,*_:case!=evidence_trial.CASES[-1])
    assert not evidence_trial.approved(tmp_path, [])
    monkeypatch.setattr(evidence_trial,'verified_decision',lambda *_:True)
    assert evidence_trial.approved(tmp_path, [])


def test_existing_quality_window_remains_tripped():
    assert overnight.saved_quality_block()


def test_v5_stops_early_on_independent_rejections(tmp_path):
    budget=grok.Budget(tmp_path/'ledger.json')
    resolver=evidence_trial.scale100.Resolver(dry_run=True,budget=budget,evidence_v5=True)
    resolver.recent_results=[{'failed':True,'repo':'a'}, {'failed':True,'repo':'a'}]
    assert not resolver.quality_tripped()
    resolver.recent_results.append({'failed':True,'repo':'b'})
    assert resolver.quality_tripped()


def test_saved_svelte_stage_rejects_boilerplate_even_if_relabelled():
    case = evidence_trial.CASES[0]
    folder = OUT/'full_cohort'/evidence_trial.NAME
    key = grok.cache_key(case[3], grok.EVIDENCE_V5)
    failure = json.loads((folder/'grok'/f'{key}.json').read_bytes())
    value = json.loads(failure['diagnostic']['raw_output'])
    source, _ = evidence_trial.source_for(case)
    assert '$props()' in source.splitlines()[7]
    assert value['evidence'] == [{'line':8, 'symbol':'$props', 'role':'declaration'}]
    for role in ('declaration', 'code'):
        value['evidence'][0]['role'] = role
        with pytest.raises(ValueError, match='Svelte runtime boilerplate'):
            grok.validate_evidence_v5(value, source)


def test_status_reports_saved_failure_without_opening_a_budget(monkeypatch,capsys):
    monkeypatch.setattr(sys,'argv',['evidence_trial.py','--status'])
    monkeypatch.setattr(evidence_trial, 'TrialBudget', lambda **_:pytest.fail('Status opened a budget'))
    evidence_trial.main()
    output=capsys.readouterr().out
    assert 'strelov1/freehire #410' in output
    assert 'Reference does not support declared role' in output
    assert 'Overnight paid dispatch stays locked' in output
