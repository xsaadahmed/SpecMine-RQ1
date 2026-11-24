import argparse
import json

import pytest

import full_cohort as cohort
import grok
import overnight
import scale100


def test_extended_budget_keeps_previous_charges_and_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(scale100, 'CACHE', tmp_path)
    cache = tmp_path / 'grok'
    cache.mkdir()
    for i in range(9):
        (cache / f'{i}.json').write_text(json.dumps({
            'status': 'validated', 'content_sha256': str(i),
        }))
    ledger = tmp_path / 'ledger.json'
    prior = [{'reported_cost_usd': .23302985, 'charged_or_reserved_usd': .23302985}]
    prior += [{'reported_cost_usd': 0, 'charged_or_reserved_usd': 0}] * 73
    ledger.write_text(json.dumps({'attempts': prior, 'smoke_validated': False}))
    budget = scale100.ScalingBudget(ledger, max_spend=7, max_requests=174)
    with pytest.raises(RuntimeError, match='spending_limit'):
        budget.reserve(6.77, 'would exceed cumulative cap')
    assert json.loads(ledger.read_text())['attempts'] == prior
    for i in range(100):
        index = budget.reserve(.06, str(i))
        budget.finish(index, actual=.03)
    with pytest.raises(RuntimeError, match='request_limit'):
        budget.reserve(.06, '101st attempt in this run')
    assert json.loads(ledger.read_text())['attempts'][:74] == prior
    at_lifetime_limit = scale100.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    at_lifetime_limit.state['attempts'] += [prior[-1]] * 826
    with pytest.raises(RuntimeError, match='request_limit'):
        at_lifetime_limit.reserve(.06, '1001st lifetime attempt')


def test_rearm_preserves_original_and_repeated_flag_cannot_reset_breaker(tmp_path, monkeypatch):
    monkeypatch.setattr(scale100, 'CACHE', tmp_path)
    original = cohort.quality_circuit_path(tmp_path)
    window = [{'origin': 'live', 'prompt_version': grok.PROMPT_VERSION,
               'cache_key': str(i), 'failed': True, 'repo': str(i % 3)} for i in range(10)]
    original.write_text(json.dumps(window))
    original_bytes = original.read_bytes()
    assert scale100.Resolver(circuit_path=original, fallback_on_quality=True).model_disabled
    trial = cohort.quality_circuit_path(tmp_path, rearm=True)
    assert trial != original and original.read_bytes() == original_bytes
    calls = []

    def reject(*args, **kwargs):
        calls.append(1)
        return {'status': 'provider_or_validation_failure', 'error_type': 'ValueError',
                'diagnostic': {'stage': 'schema_or_evidence'}}

    monkeypatch.setattr(grok.GrokResolver, 'resolve', reject)
    resolver = scale100.Resolver(circuit_path=trial, fallback_on_quality=True)
    assert not resolver.model_disabled
    for i in range(10):
        resolver.current_repo = str(i % 3)
        resolver.current_pr = i
        resolver.resolve('source', 'unit.ts', 'typescript', f'trial-{i}')
    assert resolver.model_disabled and len(calls) == 10
    assert cohort.quality_circuit_path(tmp_path) == trial
    assert cohort.quality_circuit_path(tmp_path, rearm=True) == trial
    resumed = scale100.Resolver(circuit_path=trial, fallback_on_quality=True)
    assert resumed.resolve('source', 'unit.ts', 'typescript', 'another')['status'] == 'model_quality_fallback'
    assert len(calls) == 10 and original.read_bytes() == original_bytes


def test_configured_limits_propagate_to_overnight_child():
    parser = argparse.ArgumentParser()
    cohort.add_model_limits(parser)
    args = parser.parse_args('--max-grok-spend 7 --max-grok-requests 1000 --max-new-model-calls 100'.split())
    cohort.validate_model_limits(parser, args)
    command = overnight.child_command(6, 13025, True, args.max_grok_requests,
                                      args.max_new_model_calls, args.max_grok_spend)
    child_args, _ = parser.parse_known_args(command)
    assert vars(child_args) == vars(args)
    args.max_grok_spend = float('nan')
    with pytest.raises(SystemExit):
        cohort.validate_model_limits(parser, args)
