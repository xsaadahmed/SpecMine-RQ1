"""Read-only reconciliation of the original cohort and recorded inspections."""
import csv
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from common import BASE, CACHE, KEY, OUT, file_hash, protect_prior, write_json
from detector import eligible
from full_cohort import groups
from github_http import read_count
from progress_audit import audit_pending
from scale100 import Resolver
from storage import Store, metadata_request

FOLDER = OUT / 'full_cohort'
REPORT = FOLDER / 'cohort_coverage_audit'


def identity(row):
    return row['repo_name'], int(row['pr_number'])


def records(path):
    try:
        return pd.read_csv(path).to_dict('records')
    except pd.errors.EmptyDataError:
        return []


def unique_rows(path):
    rows = records(path)
    keyed = {identity(row): row for row in rows}
    assert len(keyed) == len(rows), f'Duplicate PR identity in {path}'
    return keyed


def add_audit(path, allowed, attempted, file_evidence):
    with path.open(encoding='utf-8-sig', newline='') as source:
        for item in csv.DictReader(source):
            if not all(item.get(field) for field in KEY):
                continue
            key = identity(item)
            if key not in allowed:
                continue
            attempted.add(key)
            if item.get('examined', '').lower() == 'true' and item.get('content_sha256'):
                file_evidence.add(key)


def main():
    REPORT.mkdir(exist_ok=True)
    cohort_path = FOLDER / 'current_main_outcomes.csv'
    ledger_path = OUT / 'api_ledger.json'
    paths = sorted(FOLDER.glob('batch_*/sample.csv'))
    preserved = {p: file_hash(p) for p in [cohort_path, ledger_path, *paths]}
    cohort = unique_rows(cohort_path)
    original = pd.read_parquet(BASE / 'outputs/analysis_dataset.parquet', columns=KEY)
    assert len(original) == len(cohort) == 3186
    assert not original.duplicated(KEY).any()
    assert set(original.itertuples(index=False, name=None)) == set(cohort)
    entry = unique_rows(FOLDER / 'entry_cohort.csv')
    queue = unique_rows(FOLDER / 'unresolved_queue.csv')
    assert set(entry) == set(cohort)
    assert set(queue) == {k for k, r in entry.items() if pd.isna(r['test_added_content_verified'])}
    selected = {}
    states = {}
    checkpoint_keys = set()
    result_checkpoint_keys = set()
    attempted = set()
    inspected = set()
    file_evidence = set()
    for path in paths:
        batch = path.parent
        manifest = json.loads((batch / 'selection_integrity.json').read_bytes())
        for name, digest in manifest.items():
            assert file_hash(FOLDER / Path(name.replace('\\', '/'))) == digest, name
        sample = unique_rows(path)
        assert not set(sample).intersection(selected)
        assert set(sample) <= set(queue)
        selected.update(dict.fromkeys(sample, batch.name))
        saved_states = unique_rows(batch / 'progress_states.csv')
        assert set(saved_states) == set(sample)
        states.update(saved_states)
        for key, row in unique_rows(batch / 'outcomes.csv').items():
            if pd.notna(row['test_added_content_verified']):
                assert row['test_added_content_verified'] == cohort[key]['test_added_content_verified']
            if row.get('n_files_inspected', 0) > 0:
                inspected.add(key)
        for result in (batch / 'results').glob('*.csv'):
            assert result.stat().st_size
            for key, row in unique_rows(result).items():
                assert key in sample and key not in result_checkpoint_keys
                result_checkpoint_keys.add(key)
                if row.get('n_files_inspected', 0) > 0:
                    inspected.add(key)
        for checkpoint in (batch / 'checkpoints').glob('*.json'):
            row = json.loads(checkpoint.read_bytes())
            key = identity(row)
            assert key in sample
            checkpoint_keys.add(key)
            if (row.get('n_files_inspected') or 0) > 0:
                inspected.add(key)
            if (row.get('n_files_attempted') or 0) > 0:
                attempted.add(key)
        for audit in (batch / 'audits').glob('*.csv'):
            add_audit(audit, sample, attempted, file_evidence)
    for audit in [OUT / 'main_inspection_audit.csv', OUT / 'pilot_inspection_audit.csv',
                  FOLDER / 'inputs/inspection_audit.csv',
                  FOLDER / 'inputs/reconciled_inspection_audit.csv',
                  *FOLDER.glob('*/*offline_audit.csv'),
                  *FOLDER.glob('*/offline_inspection_audit.csv'),
                  *FOLDER.glob('*/offline_replay_evidence.csv')]:
        add_audit(audit, cohort, attempted, file_evidence)
    for source in [entry, cohort]:
        inspected.update(k for k, row in source.items() if row.get('n_files_inspected', 0) > 0)
    inspected.update(file_evidence)
    # Confirm unassigned PRs still have no cached metadata. The prior frontier
    # supplies the recorded details and must cover every unassigned unknown.
    prior_frontier = unique_rows(FOLDER / 'incident_quality_92/unknown_frontier.csv')
    stale = [cohort[key] for key, row in states.items() if pd.isna(cohort[key]['test_added_content_verified'])
             and key in prior_frontier
             and row['verification_state'] != prior_frontier[key]['verification_state']]
    refreshed = {}
    if stale:
        source = pd.DataFrame(stale)
        refreshed = {identity(row): row for row in audit_pending(
            source, source, groups(), Resolver(dry_run=True)).to_dict('records')}
    store = Store()
    rows = []
    for key, row in cohort.items():
        outcome = row['test_added_content_verified']
        batch = selected.get(key)
        saved = states.get(key, {}).get('verification_state', '')
        status = refreshed.get(key, states.get(key, {})).get('verification_state', '')
        details = refreshed.get(key, states.get(key, {})).get('details', '')
        if pd.isna(outcome) and not batch:
            assert key in prior_frontier
            req = metadata_request(*key)
            cached_metadata = store.record(req)
            status = 'not_yet_examined' if cached_metadata is None else prior_frontier[key]['verification_state']
            details = prior_frontier[key]['details']
        if key in inspected:
            category = 'source_inspected'
        elif pd.notna(outcome):
            assert outcome == 0 and row.get('n_eligible_added_files') == 0
            category = 'verified_no_eligible_files'
        elif not batch and status == 'not_yet_examined':
            category = 'unassigned_never_started'
        else:
            category = 'source_not_inspected_blocked_or_pending'
        rows.append(dict(zip(KEY, key), batch=batch, verification_state=status,
                         saved_verification_state=saved,
                         outcome=outcome, coverage=category,
                         file_inspection_audit=key in file_evidence,
                         source_attempt_record=key in attempted,
                         batch_engine_checkpoint=key in checkpoint_keys,
                         batch_result_checkpoint=key in result_checkpoint_keys, details=details))
    report = pd.DataFrame(rows)
    unknown = report[report.outcome.isna()]
    new = unknown[unknown.coverage.eq('unassigned_never_started')]
    assert set(new[KEY].itertuples(index=False, name=None)) == set(queue) - set(selected)
    report.to_csv(REPORT / 'all_prs.csv', index=False)
    new.to_csv(REPORT / 'unassigned_never_started.csv', index=False)

    # Conservative request upper bound from frozen paths, before cache hits or early exits.
    file_rows = pd.read_parquet(BASE / 'outputs/intermediate/classified_files.parquet',
                                columns=KEY + ['file_path', 'change_status'])
    targets = new[KEY].merge(file_rows, on=KEY, validate='one_to_many')
    counts = targets.groupby(KEY).size()
    content = sum(eligible(path) for path in targets.loc[targets.change_status.eq('added'), 'file_path'])
    ledger = json.loads(ledger_path.read_bytes())['attempts']
    used = read_count(CACHE)
    summary = {
        'cohort': len(report), 'original_verified_at_batch_entry': len(entry) - len(queue),
        'selected_unique': len(selected), 'batch_engine_checkpoints': len(checkpoint_keys),
        'batch_result_checkpoints': len(result_checkpoint_keys),
        'refreshed_stale_states': len(refreshed),
        'coverage': report.coverage.value_counts().to_dict(),
        'unknown_coverage': unknown.coverage.value_counts().to_dict(),
        'unknown_state_by_coverage': {
            category: part.verification_state.value_counts().to_dict()
            for category, part in unknown.groupby('coverage')
        },
        'unknown_reason_counts': dict(Counter(
            str(detail) for raw in unknown.details if isinstance(raw, str) and raw
            for detail in json.loads(raw) if not isinstance(detail, dict))),
        'batch7_frozen_path_request_estimate': {
            'metadata': len(new), 'file_list_pages': int((counts.add(99) // 100).sum()),
            'eligible_added_content': int(content),
        },
        'github_requests_used': used, 'github_requests_remaining': max(0, 13025 - used),
        'grok_attempts': len(ledger),
        'grok_charged_or_reserved_usd': sum(row['charged_or_reserved_usd'] for row in ledger),
    }
    assert all(file_hash(p) == digest for p, digest in preserved.items())
    summary['frozen_research_checks'] = protect_prior()
    write_json(REPORT / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
