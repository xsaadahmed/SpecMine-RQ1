import json

import grpc
import pytest

from common import CACHE, OUT, sha256
import grok
import scale100 as engine
from test_grok import GOOD, SOURCE


KEY = '2feb2746cd238ffcac8a4b54bf77061c1e398fec597b696eff61aa2a9025d581'
PATH = 'scripts/test_hk_smart_analysis.sh'


class ProviderError(grpc.RpcError):
    def __init__(self, status):
        self.status = status

    def code(self):
        return self.status

    def details(self):
        pytest.fail('Raw provider details must not be read')


@pytest.fixture
def trial(tmp_path, monkeypatch):
    cache = tmp_path / 'grok'
    cache.mkdir()
    for i in range(9):
        (cache / f'validated-{i}.json').write_text(json.dumps({
            'status': 'validated', 'content_sha256': str(i),
        }))
    ledger = tmp_path / 'api_ledger.json'
    ledger.write_bytes((OUT / ledger.name).read_bytes())
    monkeypatch.setattr(engine, 'CACHE', tmp_path)
    monkeypatch.setattr(grok, 'CACHE', tmp_path)
    monkeypatch.setenv('XAI_API_KEY', 'offline-test-key')
    return cache, ledger


def test_actual_legacy_failure_is_cached_unknown_and_reservation_allows_resume(trial):
    cache, ledger = trial
    failed = (CACHE / 'grok' / f'{KEY}.json').read_bytes()
    (cache / f'{KEY}.json').write_bytes(failed)
    record = json.loads(failed)
    raw = (OUT / 'content' / f"{record['content_sha256']}.txt").read_bytes()
    assert sha256(raw) == record['content_sha256']
    assert record['diagnostic']['stage'] == 'transport'
    assert 'raw_output' not in record['diagnostic']
    budget = engine.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    prior = json.loads(ledger.read_bytes())['attempts']
    attempt = next(row for row in prior if row['task'] == KEY and 'reported_cost_usd' not in row)
    assert attempt['charged_or_reserved_usd'] == .06
    resolver = engine.Resolver(dry_run=False, budget=budget,
                               transport=lambda *_: pytest.fail('Retry of cached failure'))
    result = resolver.resolve(raw.decode('utf-8-sig'), PATH, 'shell', record['content_sha256'])
    assert result['cache_hit'] and result['has_executable_tests'] is None
    assert not resolver.recent_results
    assert budget.reserve(.06, 'new-source') == len(prior)
    assert budget.state['attempts'][:-1] == prior
    assert (cache / f'{KEY}.json').read_bytes() == failed


def test_transient_provider_failure_retries_with_separate_reservation(trial, monkeypatch):
    _, ledger = trial
    budget = engine.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    calls = []
    delays = []
    monkeypatch.setattr(grok.time, 'sleep', delays.append)

    def transport(*_):
        calls.append(1)
        if len(calls) == 1:
            raise ProviderError(grpc.StatusCode.DEADLINE_EXCEEDED)
        return json.dumps(GOOD), {}, .001, 'REASON_STOP'

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport)
    assert resolver.resolve(SOURCE, 'test.js', 'javascript', 'retry-source')['status'] == 'validated'
    assert len(calls) == 2 and delays == [1]
    first, second = budget.state['attempts'][-2:]
    assert first['transport_status'] == 'DEADLINE_EXCEEDED'
    assert first['charged_or_reserved_usd'] == first['reserved_usd']
    assert second['charged_or_reserved_usd'] == .001
    assert len(resolver.recent_results) == 1 and not resolver.recent_results[0]['failed']


@pytest.mark.parametrize('status, attempts', [
    (grpc.StatusCode.UNAVAILABLE, 3), (grpc.StatusCode.UNAUTHENTICATED, 1),
])
def test_systemic_provider_failures_stop_and_cached_result_stays_unknown(
        trial, monkeypatch, status, attempts):
    _, ledger = trial
    monkeypatch.setattr(grok.time, 'sleep', lambda _: None)
    budget = engine.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    before = len(budget.state['attempts'])

    def transport(*_):
        raise ProviderError(status)

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport)
    with pytest.raises(RuntimeError, match=f'model_transport_failure_{status.name}'):
        resolver.resolve(SOURCE, 'test.js', 'javascript', 'outage-source')
    assert len(budget.state['attempts']) == before + attempts
    assert not resolver.recent_results
    result = resolver.resolve(SOURCE, 'test.js', 'javascript', 'outage-source')
    assert result['cache_hit'] and result['has_executable_tests'] is None
    assert result['diagnostic']['transport_status'] == status.name
    assert len(budget.state['attempts']) == before + attempts


def test_retry_cannot_exceed_spending_reservation(trial, monkeypatch):
    _, ledger = trial
    spent = sum(row['charged_or_reserved_usd'] for row in json.loads(ledger.read_bytes())['attempts'])
    budget = engine.ScalingBudget(ledger, max_spend=spent + .07, max_requests=1000)
    before = len(budget.state['attempts'])
    monkeypatch.setattr(grok.time, 'sleep', lambda _: None)

    def transport(*_):
        raise ProviderError(grpc.StatusCode.UNAVAILABLE)

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport)
    with pytest.raises(RuntimeError, match='stopped_spending_limit'):
        resolver.resolve(SOURCE, 'test.js', 'javascript', 'budget-source')
    assert len(budget.state['attempts']) == before + 1


def test_unaccounted_reservation_still_fails_closed():
    assert not engine.ScalingBudget.accounted_attempt({
        'status': 'failed_or_invalid_reserved', 'charged_or_reserved_usd': .01,
        'reserved_usd': .06,
    })


def seed_transport_block(trial):
    cache, ledger = trial
    state = json.loads(ledger.read_bytes())
    keys = (
        '3bf1c4040eee4aec91c4336a92889ed3943da6e0a8b355c99739422760736f66',
        '46e8f71e12015a7101c104935303e9dc693d8c311ed67f26cc318fecf66357bc',
    )
    last = next(i for i, row in enumerate(state['attempts']) if row['task'] == keys[-1])
    state['attempts'] = state['attempts'][:last + 1]
    ledger.write_text(json.dumps(state))
    assert [row['task'] for row in state['attempts'][-2:]] == list(keys)
    for key in keys:
        (cache / f'{key}.json').write_bytes((CACHE / 'grok' / f'{key}.json').read_bytes())
    return engine.ScalingBudget(ledger, max_spend=7, max_requests=1000), state


def test_actual_consecutive_invalid_arguments_block_new_dispatch(trial):
    _, ledger = trial
    budget, state = seed_transport_block(trial)
    resolver = engine.Resolver(dry_run=False, budget=budget,
                               transport=lambda *_: pytest.fail('Dispatched after repeated rejections'))
    result = resolver.resolve(SOURCE, 'test.js', 'javascript', 'new-source')
    assert result['status'] == 'model_transport_blocked_invalid_argument'
    assert result['has_executable_tests'] is None and not resolver.recent_results
    assert json.loads(ledger.read_bytes()) == state


def test_rearm_keeps_history_and_limits_fresh_dispatch_to_two_attempts(trial):
    cache, ledger = trial
    budget, state = seed_transport_block(trial)
    old_key = state['attempts'][-1]['task']
    failed = (cache / f'{old_key}.json').read_bytes()
    calls = []

    def transport(*_):
        calls.append(1)
        return json.dumps(GOOD), {}, .001, 'REASON_STOP'

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport,
                               rearm_transport=True)
    assert resolver.transport_rearmed and not resolver.transport_blocked
    old_digest = json.loads(failed)['content_sha256']
    assert resolver.resolve(SOURCE, 'old.vue', 'vue', old_digest)['cache_hit']
    assert not calls
    for source_hash in ('fresh1', 'fresh2'):
        assert resolver.resolve(SOURCE, 'test.js', 'javascript', source_hash)['status'] == 'validated'
    with pytest.raises(RuntimeError, match='stopped_request_limit'):
        resolver.resolve(SOURCE, 'test.js', 'javascript', 'fresh3')
    assert len(calls) == 2
    saved = json.loads(ledger.read_bytes())['attempts']
    assert saved[:-2] == state['attempts']
    assert all(row['transport_rearm_probe'] for row in saved[-2:])
    assert (cache / f'{old_key}.json').read_bytes() == failed
    resumed_budget = engine.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    assert not engine.Resolver(dry_run=False, budget=resumed_budget).transport_blocked


def test_failed_rearm_stays_blocked_across_runs(trial):
    _, ledger = trial
    budget, state = seed_transport_block(trial)

    def reject(*_):
        raise ProviderError(grpc.StatusCode.UNAUTHENTICATED)

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=reject,
                               rearm_transport=True)
    with pytest.raises(RuntimeError, match='model_transport_failure_UNAUTHENTICATED'):
        resolver.resolve(SOURCE, 'test.js', 'javascript', 'probe')
    saved = json.loads(ledger.read_bytes())['attempts']
    assert saved[:-1] == state['attempts']
    assert saved[-1]['transport_rearm_probe']
    assert saved[-1]['charged_or_reserved_usd'] == saved[-1]['reserved_usd']
    resumed = engine.Resolver(dry_run=False, budget=engine.ScalingBudget(ledger),
                              transport=lambda *_: pytest.fail('Unexpected retry'))
    assert resumed.resolve(SOURCE, 'test.js', 'javascript', 'another')['status'] == (
        'model_transport_blocked_invalid_argument'
    )


def test_cohort_checkpoint_can_keep_unknown_when_request_limit_hits_mid_pr(trial, monkeypatch):
    import pipeline

    budget, state = seed_transport_block(trial)
    calls = []

    def transport(*_):
        calls.append(1)
        # Valid response envelope, but missing the evidence required for a decision.
        return '{}', {}, .001, 'REASON_STOP'

    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport,
                               rearm_transport=True, defer_request_limit=True)
    files = [{'filename': f'src/{i}.js', 'status': 'added'} for i in range(4)]
    inspected = []

    def deterministic(text, path, digest):
        return {'language': 'javascript', 'classification': 'uncertain',
                'has_executable_tests': None, 'needs_review': True, 'method': 'deterministic'}

    monkeypatch.setattr(pipeline, 'static_prediction', deterministic)

    def classify(text, file, provenance):
        path = file['filename']
        if path == 'src/3.js':
            return {'classification': 'automated_test', 'has_executable_tests': True,
                    'needs_review': False, 'method': 'deterministic', 'evidence': ['test body']}
        value, ai = pipeline.hybrid(text, path, provenance['content_sha256'], resolver)
        inspected.append(ai['status'])
        return value

    def fetch(file):
        return SOURCE, {'content_sha256': file['filename']}, None

    outcome, audit, _ = pipeline.search_pr(files[:3], fetch, classify)
    assert outcome['test_added_content_verified'] is None
    assert len(audit) == 3 and inspected[-1] == 'request_limit'
    outcome, _, _ = pipeline.search_pr(files, fetch, classify)
    assert outcome['test_added_content_verified'] == 1
    assert len(calls) == 2 and len(budget.state['attempts']) == len(state['attempts']) + 2


def test_transport_rearm_cannot_override_model_quality(trial, monkeypatch):
    budget, state = seed_transport_block(trial)
    monkeypatch.setattr(engine.Resolver, 'quality_tripped', lambda _: True)
    resolver = engine.Resolver(dry_run=False, budget=budget, rearm_transport=True,
                               fallback_on_quality=True,
                               transport=lambda *_: pytest.fail('Quality fallback was bypassed'))
    assert resolver.resolve(SOURCE, 'test.js', 'javascript', 'fresh')['status'] == (
        'model_quality_fallback'
    )
    assert budget.state['attempts'] == state['attempts']


def test_invalid_argument_logs_field_mentions_without_provider_text(trial):
    cache, ledger = trial

    class Rejected(ProviderError):
        def details(self):
            return 'Invalid response_format schema. Echoed private request data.'

        def trailing_metadata(self):
            return [('x-request-id', '12345678-abcd-1234-abcd-123456789abc'),
                    ('authorization', 'private metadata')]

    def transport(*_):
        raise Rejected(grpc.StatusCode.INVALID_ARGUMENT)

    budget = engine.ScalingBudget(ledger, max_spend=7, max_requests=1000)
    resolver = engine.Resolver(dry_run=False, budget=budget, transport=transport)
    with pytest.raises(RuntimeError, match='model_transport_failure_INVALID_ARGUMENT'):
        resolver.resolve(SOURCE, 'test.js', 'javascript', 'rejected')
    saved = (cache / f"{grok.cache_key('rejected')}.json").read_text()
    diagnostic = json.loads(saved)['diagnostic']
    assert diagnostic['provider_field_mentions'] == ['response_format', 'schema']
    assert diagnostic['provider_request_id'] == '12345678-abcd-1234-abcd-123456789abc'
    assert diagnostic['payload_bytes'] > 0 and len(diagnostic['payload_sha256']) == 64
    assert 'private request data' not in saved
    assert 'private metadata' not in saved


@pytest.mark.parametrize('key, filename, payload_size', [
    ('3bf1c4040eee4aec91c4336a92889ed3943da6e0a8b355c99739422760736f66',
     'AgentDebugSidebar.vue', 4189),
    ('46e8f71e12015a7101c104935303e9dc693d8c311ed67f26cc318fecf66357bc',
     'DebugMessage.vue', 10181),
])
def test_failed_vue_inputs_serialize_through_installed_sdk(monkeypatch, key, filename, payload_size):
    from types import SimpleNamespace

    import xai_sdk
    from xai_sdk.proto import chat_pb2
    from xai_sdk.sync.chat import Client

    record = json.loads((CACHE / 'grok' / f'{key}.json').read_bytes())
    digest = record['content_sha256']
    raw = (OUT / 'content' / f'{digest}.txt').read_bytes()
    assert sha256(raw) == digest
    source, _ = grok.sanitize(raw.decode('utf-8-sig'))
    assert sha256(source.encode()) == record['diagnostic']['sanitized_input_sha256']
    assert sha256(grok.SYSTEM.encode()) == record['diagnostic']['prompt_sha256']
    assert record['diagnostic']['complete_input'] and len(source.encode()) < grok.MAX_BYTES
    payload = grok.classification_payload(
        f'frontend/src/views/chat/components/{filename}', 'vue', source, True, [],
    )
    assert len(payload.encode()) == payload_size
    assert json.loads(payload)['source_code'].splitlines() == [
        f'{i}: {line}' for i, line in enumerate(source.splitlines(), 1)
    ]
    requests = []

    class Captured(Exception):
        pass

    def capture(request):
        requests.append(chat_pb2.GetCompletionsRequest.FromString(request.SerializeToString()))
        raise Captured

    client = object.__new__(Client)
    client._stub = SimpleNamespace(GetCompletion=capture)
    monkeypatch.setattr(xai_sdk, 'Client', lambda **_: SimpleNamespace(chat=client))
    monkeypatch.setenv('XAI_API_KEY', 'offline-test-key')
    with pytest.raises(Captured):
        grok.sdk_call(grok.SYSTEM, payload)
    request, = requests
    assert request.model == 'grok-4.3'
    assert request.reasoning_effort == chat_pb2.EFFORT_NONE
    assert (request.max_tokens, request.temperature, request.n) == (1200, 0, 1)
    assert not request.store_messages and len(request.messages) == 2
    assert request.response_format.format_type == chat_pb2.FORMAT_TYPE_JSON_SCHEMA
    assert json.loads(request.response_format.schema) == grok.WireClassification.model_json_schema()
