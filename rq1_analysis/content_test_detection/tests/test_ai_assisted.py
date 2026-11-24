import json
import shutil

import pytest

import ai_assisted as ai


def test_actual_trial_spans_both_classes_and_replays_frozen_ai_source():
    items, plan = ai.trial_plan()
    assert plan['human_reviewed'] is False
    assert sum(i['classification']=='automated_test' for i in items)==3
    assert sum(i['classification']=='not_test' for i in items)==3
    for item in items:
        text = ai.review.source(item)
        assert ai.grok.sanitize(text)[0]==text
        choices, source = ai.catalog(item,text)
        assert source['anchors'] and source['source']
        assert len(choices)>1


def test_unrelated_citations_and_correctly_grounded_classification_are_distinct():
    item = ai.trial_plan()[0][0]
    choices, source = ai.catalog(item,ai.review.source(item))
    supported = next(k for k,v in choices.items() if v==[source['start'],source['end']])
    other = next(k for k in choices if k!=supported)
    schema = ai.wire(choices)
    def evaluate(judgment,reference):
        return ai.assess(json.dumps({'judgment':judgment,'reference_id':reference}),
                         schema,choices,source)
    assert evaluate('automated_test',supported)=='validated_agreement'
    assert evaluate('automated_test',other)=='unsupported_citation'
    assert evaluate('not_test',supported)=='classification_disagreement'
    assert evaluate('uncertain','none')=='abstained'
    with pytest.raises(ValueError):
        evaluate('automated_test','fabricated')


def test_prior_responses_revalidated_with_cash_ledger_and_source():
    earlier,_ = ai.pinned_references()
    for identifier in ('F06','F11'):
        result = ai.restore_prior(earlier[identifier])
        assert result['status']=='validated_agreement'
        assert result['evidence']['classification']=='not_test'
        assert result['evidence']['parsed_declaration']


def test_framework_recovery_uses_registration_and_actual_assertion():
    _, candidates = ai.pinned_references()
    item = candidates['galax-io/gatling-picatinny',222]
    text = ai.review.source(item)
    value = ai.registered_case(text,item['file_path'])
    assert value['has_executable_tests'] and len(value['evidence'])==2
    assert ai.registered_case(text.replace('shouldBe','observe'),item['file_path']) is None
    ruby = candidates['baizhiheizi/quill',1822]
    source = ai.review.source(ruby)
    assert ai.registered_case(source,ruby['file_path']) is None
    assert ai.registered_case(source.replace('< IntegrationTestCase','< ActionDispatch::IntegrationTest'),
                              ruby['file_path'])['has_executable_tests']


def test_windows_compat_header_requires_no_other_source_constructs():
    _, candidates = ai.pinned_references()
    item = candidates['hugr-lab/mssql-extension',17]
    text = ai.review.source(item)
    outcome = ai.windows_type_header(text,item['file_path'])
    assert outcome['classification']=='not_test'
    assert ai.windows_type_header(text.replace('typedef SSIZE_T ssize_t;',
                                              'static_assert(sizeof(int)>0);'),item['file_path']) is None
    assert ai.windows_type_header(text.replace('<BaseTsd.h>','"test.hpp"'),item['file_path']) is None


def test_actual_retry_context_does_not_retroactively_unlock_dispatch(tmp_path,monkeypatch):
    def capture(path,data,**options):
        assert path.name=='citation_repair_offline_diagnostic.json'
        assert data['selected_range']==[68,70]
        assert data['contextual_source_evidence']['start']==69
        assert data['contextual_source_evidence']['end']==75
        assert data['recorded_trial_passed'] is data['paid_dispatch_approved'] is False
    monkeypatch.setattr(ai,'write_json',capture)
    ai.diagnose_citation_repair()
    budget = ai.scale100.ScalingBudget(max_spend=7,max_requests=1000)
    with pytest.raises(RuntimeError,match='did not pass'):
        ai.read_approved(budget)


def test_unapproved_cohort_and_no_paid_retry_without_response(tmp_path, monkeypatch):
    monkeypatch.setattr(ai,'DEST',tmp_path)
    monkeypatch.setattr(ai.grok,'sdk_call', lambda *a,**k: pytest.fail('No paid requests'))
    budget = ai.grok.Budget(path=tmp_path/'ledger.json')
    with pytest.raises(RuntimeError,match='trial has not passed'):
        ai.read_approved(budget)
    item = ai.trial_plan()[0][0]
    budget.reserve(.06,ai.task(item))
    assert ai.paid(item,budget,dispatch=False) is None
    with pytest.raises(RuntimeError,match='interrupted reservation'):
        ai.paid(item,budget)


def test_mocked_mixed_class_trial_unlocks_only_with_intact_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(ai,'DEST',tmp_path)
    ai.setup()
    budget = ai.grok.Budget(path=tmp_path/'ledger.json')
    monkeypatch.setattr(ai.scale100,'ScalingBudget',lambda **_: budget)
    monkeypatch.setattr(ai,'scoped_provider_guard',lambda budget: None)
    roles = iter(ai.trial_plan()[0])
    def fake_provider(prompt,payload,response_format):
        case = next(roles)
        decoded = json.loads(payload)
        picked = next(k for k,v in decoded['source_ranges'].items() if
                      v==[case['basis_start'],case['basis_end']])
        return json.dumps({'judgment':case['classification'],'reference_id':picked}),{},.001,'REASON_STOP'
    monkeypatch.setattr(ai.grok,'sdk_call',fake_provider)
    ai.trial()
    assert len(budget.state['attempts'])==6
    ai.read_approved(budget)
    target = next((tmp_path/'decisions').glob('*.json'))
    target.write_text('{}')
    with pytest.raises(RuntimeError,match='source-supported agreement'):
        ai.read_approved(budget)


def test_actual_svelte_import_citation_is_still_rejected_after_repair():
    items, plan = ai.citation_repair_plan()
    assert plan['maximum_new_attempts']==5
    item = items[1]
    original = {key:value for key,value in item.items() if key!='citation_repair'}
    old = json.loads((ai.DEST/'decisions'/f'{ai.task(original)}.json').read_bytes())
    choices, support = ai.catalog(item,ai.review.source(item))
    assert ai.assess(old['raw_output'],ai.wire(choices),choices,support)=='unsupported_citation'
    formatter = next(key for key,span in choices.items() if span==[27,32])
    response = json.dumps({'judgment':'not_test','reference_id':formatter})
    assert ai.assess(response,ai.wire(choices),choices,support)=='validated_agreement'
    assert ai.task(item)!=ai.task(original)


def test_mocked_repair_carries_known_positive_without_respending(tmp_path,monkeypatch):
    old_dest = ai.DEST
    items,_ = ai.citation_repair_plan()
    for name in ('trial_result.json','trial_plan.json'):
        shutil.copyfile(old_dest/name,tmp_path/name)
    (tmp_path/'decisions').mkdir()
    original = json.loads((old_dest/'trial_result.json').read_bytes())
    for key in original['hashes']:
        name = f'{key}.json'
        shutil.copyfile(old_dest/'decisions'/name,tmp_path/'decisions'/name)
    ledger = tmp_path/'ledger.json'
    history = json.loads((ai.OUT/'api_ledger.json').read_bytes())
    history['attempts'] = history['attempts'][:next(
        index for index,row in enumerate(history['attempts']) if row['task']==list(original['hashes'])[-1])+1]
    ai.write_json(ledger,history)
    budget = ai.scale100.ScalingBudget(path=ledger,max_spend=7,max_requests=1000)
    before = len(budget.state['attempts'])
    monkeypatch.setattr(ai,'DEST',tmp_path)
    monkeypatch.setattr(ai.scale100,'ScalingBudget',lambda **_: budget)
    roles = iter(items[1:])
    def provider(prompt,payload,response_format):
        item = next(roles)
        assert prompt==(ai.REPAIR_PROMPT if item.get('citation_repair') else ai.PROMPT)
        choices = json.loads(payload)['source_ranges']
        selected = next(key for key,span in choices.items() if span==[item['basis_start'],item['basis_end']])
        return json.dumps({'judgment':item['classification'],'reference_id':selected}),{},.001,'REASON_STOP'
    monkeypatch.setattr(ai.grok,'sdk_call',provider)
    ai.repair_trial()
    assert len(budget.state['attempts'])==before+5
    assert not json.loads((tmp_path/'trial_result.json').read_bytes())['passed']
    ai.read_approved(budget)
    with pytest.raises(RuntimeError,match='already started'):
        ai.repair_trial()
