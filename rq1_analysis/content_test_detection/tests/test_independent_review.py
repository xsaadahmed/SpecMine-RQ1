import json
import shutil
import sys

import pandas as pd
import pytest

import cohort_overlay as overlay
import full_cohort
import independent_review as review
from common import KEY


def count_fixture():
    packet = review.manifest_items()
    assert len(packet) == 12
    return packet


def test_installed_overlay_matches_versioned_cohort_and_preserves_old_labels():
    root = full_cohort.DEST
    original = pd.read_csv(overlay.prefrozen_main(root))
    current = pd.read_csv(root / 'current_main_outcomes.csv')
    historical = original[original[overlay.LABEL].notna()]
    pd.testing.assert_series_equal(current.set_index(KEY)[overlay.LABEL].loc[
        historical.set_index(KEY).index], historical.set_index(KEY)[overlay.LABEL])
    delta = overlay.read_delta(root)
    assert overlay.counts(delta) == {'positive': 39, 'negative': 8, 'unknown': 0}
    pd.testing.assert_series_equal(current.set_index(KEY)[overlay.LABEL].loc[
        delta.set_index(KEY).index], delta.set_index(KEY)[overlay.LABEL], check_dtype=False)


def test_overlay_publish_replaces_stale_unknown_without_changing_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(full_cohort, 'DEST', tmp_path)
    monkeypatch.setattr(full_cohort, 'BATCH', 'batch_0001')
    folder = tmp_path / 'batch_0001' / 'results'
    folder.mkdir(parents=True)
    label = overlay.LABEL
    entry = pd.DataFrame([['org/project', 10, None], ['org/project', 11, 0.0]], columns=[*KEY, label])
    old = folder / 'prior.csv'
    entry.iloc[[0]].to_csv(old, index=False)
    original = old.read_bytes()
    delta = pd.DataFrame([['org/project', 10, 1.0]], columns=[*KEY, label])
    monkeypatch.setattr(overlay, 'read_delta', lambda _: delta)
    stats = full_cohort.publish(entry, entry.iloc[[0]][KEY])
    assert stats['batch']['positive'] == stats['batch']['checkpoint_records'] == 1
    assert stats['main'] == {'positive': 1, 'negative': 1, 'unknown': 0}
    assert old.read_bytes() == original
    conflicting = entry.copy()
    conflicting.loc[0, label] = 0
    with pytest.raises(RuntimeError, match='Conflicting verified labels'):
        overlay.apply_delta(conflicting, delta)


def test_blind_packet_has_no_labels_and_full_reverified_source():
    packet = count_fixture()
    page = (review.FOLDER / 'source_review.html').read_text(encoding='utf-8')
    assert '<script>' not in page and 'historical_reference' not in page
    for item in packet:
        text = review.source(item)
        assert len(text.splitlines()) == item['line_count']
        assert item['content_sha256'] in page
    assert all(len(item['catalog']) > 0 for item in packet if item['trial_candidate'])


def synthetic_rows(packet):
    # Exercise the importer in a temp directory, without producing research labels.
    rows = []
    for item in packet:
        label = item['historical_reference'] or 'not_test'
        if review.identity(item)[:2] == review.SCOPE_CHALLENGE:
            label = 'uncertain'
        anchor = next(iter(item['catalog'].values()), {'line': 1})
        rows.append({**item, 'label': label, 'reviewer_id': 'test-fixture',
                     'basis_start': anchor['line'], 'basis_end': anchor['line'],
                     'notes': 'Synthetic importer regression, not a research annotation'})
    return rows


def test_import_validates_actual_pinned_sources_reports_old_failure_and_locks_disagreement(tmp_path):
    packet = count_fixture()
    rows = synthetic_rows(packet)
    path = tmp_path / 'worksheet.csv'
    path.write_bytes(review.csv_bytes(rows, review.FIELDS + review.INPUT))
    annotations = review.validated_labels(path, packet)
    report = review.evaluate(packet, annotations)
    assert report['offline_gate_passed'] and len(report['trial_review_ids']) == 2
    assert report['new_strategy_live_metrics'] is None
    assert report['archived_unsupported_evidence_numerator'] > 0
    assert any(r['evidence_status'] == 'evidence_rejected'
               and r['prompt_version'] == review.grok.EVIDENCE_V5
               for r in report['archived_model_responses'])
    control = next(row for row in rows if row['historical_reference'])
    annotations[control['review_id']]['label'] = (
        'automated_test' if control['label'] == 'not_test' else 'not_test')
    assert not review.evaluate(packet, annotations)['offline_gate_passed']
    rows[0]['content_sha256'] = 'a' * 64
    path.write_bytes(review.csv_bytes(rows, review.FIELDS + review.INPUT))
    with pytest.raises(ValueError, match='identity'):
        review.validated_labels(path, packet)


def test_live_requires_import_before_provider_init(tmp_path, monkeypatch):
    path = tmp_path / 'worksheet.csv'
    path.write_bytes(b'blank')
    monkeypatch.setattr(review.grok, 'sdk_call', lambda *a, **k: pytest.fail('must not dispatch'))
    with pytest.raises(RuntimeError, match='Import an independently completed worksheet'):
        review.live_trial(path)


def test_regular_live_runner_cannot_bypass_independent_trial(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['full_cohort.py', '--live', '--rearm-model-quality'])
    monkeypatch.setattr(full_cohort, 'freeze_inputs', lambda: pytest.fail('must stop before scheduling'))
    with pytest.raises(SystemExit) as exc:
        full_cohort.main()
    assert exc.value.code == 2


def test_trial_checks_real_single_file_prs_and_stops_without_repeating(tmp_path, monkeypatch):
    packet = count_fixture()
    for filename in ('labels_blank.csv', 'source_review.html', 'review_manifest.json'):
        shutil.copyfile(review.FOLDER / filename, tmp_path / filename)
    monkeypatch.setattr(review, 'FOLDER', tmp_path)
    monkeypatch.setenv('XAI_API_KEY', 'offline-test-stub')
    worksheet = tmp_path / 'labels_completed.csv'
    worksheet.write_bytes(review.csv_bytes(synthetic_rows(packet), review.FIELDS + review.INPUT))
    assert review.import_labels(worksheet, independent=True)['offline_gate_passed']
    budget = review.scale100.ScalingBudget(path=tmp_path / 'ledger.json', max_spend=7, max_requests=1000)
    monkeypatch.setattr(review.scale100, 'ScalingBudget', lambda **_: budget)
    calls = []

    def provider(prompt, payload, response_format):
        calls.append(json.loads(payload))
        return '{"judgment":"uncertain","reference_id":"none"}', {}, .01, 'REASON_STOP'

    monkeypatch.setattr(review.grok, 'sdk_call', provider)
    review.live_trial(worksheet)
    assert len(calls) == len(budget.state['attempts']) == 1
    assert calls[0]['complete_file']
    assert json.loads((tmp_path / 'trial_result.json').read_bytes())['passed'] is False
    with pytest.raises(RuntimeError, match='already reserved or attempted'):
        review.live_trial(worksheet)
    assert len(calls) == 1


@pytest.mark.parametrize(('variant', 'status'), [
    ('valid', 'validated_agreement'),
    ('out_of_review_range', 'unsupported_by_independent_review'),
    ('invented', 'invalid_reference_or_response'),
    ('abstain', 'abstained'),
    ('no_receipt', 'missing_billing_receipt'),
    ('transport', 'provider_error'),
])
def test_bounded_case_with_real_sources_and_mocked_transport(tmp_path, monkeypatch, variant, status):
    item = next(item for item in count_fixture() if item['trial_candidate'])
    text = review.source(item)
    catalog = item['catalog']
    key, ref = next(iter(catalog.items()))
    line = ref['line'] + int(variant == 'out_of_review_range')
    reference = {'label': 'not_test', 'basis_start': line, 'basis_end': line}
    schema_seen = []

    def provider(prompt, payload, response_format):
        schema_seen.append(response_format.model_json_schema())
        if variant == 'transport':
            raise RuntimeError('Details must not be retained')
        decision = {'judgment': 'not_test', 'reference_id': key}
        if variant == 'invented':
            decision['reference_id'] = 'made_up'
        if variant == 'abstain':
            decision.update(judgment='uncertain', reference_id='none')
        return json.dumps(decision), {}, None if variant == 'no_receipt' else .01, 'REASON_STOP'

    monkeypatch.setattr(review, 'FOLDER', tmp_path)
    monkeypatch.setattr(review.grok, 'sdk_call', provider)
    budget = review.grok.Budget(path=tmp_path / 'ledger.json')
    saved = review.run_case(item, text, catalog, '{}', .06, reference, budget)
    assert saved['status'] == status
    assert len(schema_seen) == len(budget.state['attempts']) == 1
    expected = .06 if variant in {'transport', 'no_receipt'} else .01
    assert budget.state['attempts'][0]['charged_or_reserved_usd'] == expected
    assert saved['schema']['properties']['reference_id']['enum'] == [*catalog, 'none']
    assert 'Details must not be retained' not in json.dumps(saved)
