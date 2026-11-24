"""Audit the Nov. 23 model tranche and cohort frontier entirely offline."""
import json
import pandas as pd

import full_cohort
import grok
from common import CACHE, KEY, OUT, file_hash, protect_prior, sha256, write_json
from progress_audit import audit_pending
import scale100
from detector import classify
from scale100 import Resolver

ROOT = OUT / 'full_cohort'
REPORT = ROOT / 'incident_quality_92'
RECOVERY = '1382aa0b37abfe1adad5a68336d2dee01a1ae5e196f920202a3d91546235538d'


def classify_frontier(row):
    details = json.loads(row.details)
    if row.verification_state == 'cache_ready_for_replay':
        return 'offline_cache_or_deterministic', 0, 0
    if row.verification_state in {'not_yet_examined', 'waiting_github_content'}:
        return 'github_acquisition', 0, 0
    if row.verification_state == 'missing_or_changed_github_data':
        return 'github_reconciliation', 0, 0
    fresh = sum(isinstance(d, dict) and d.get('model_status') in {
        'dry_run', 'missing_XAI_API_KEY'} for d in details)
    remaining = max(0, len(details) - fresh)
    if remaining:
        return ('mixed_manual_and_model' if fresh else 'manual_or_unavailable',
                fresh, remaining)
    return 'model_only', fresh, 0


def main():
    REPORT.mkdir(exist_ok=True)
    ledger = OUT / 'api_ledger.json'
    outcomes = ROOT / 'current_main_outcomes.csv'
    batch = ROOT / 'batch_0006/outcomes.csv'
    protected = [ledger, outcomes, batch, ROOT / 'batch_0006/sample.csv']
    attempts = json.loads(ledger.read_bytes())['attempts'][81:92]
    assert len(attempts) == 11
    records = {a['task']: CACHE / 'grok' / (a['task'] + '.json') for a in attempts}
    hashes = {p: file_hash(p) for p in protected + list(records.values())}
    identities = {}
    for file in (ROOT / 'batch_0006/audits').glob('*.csv'):
        if not file.stat().st_size:
            continue
        try:
            frame = pd.read_csv(file)
        except pd.errors.EmptyDataError:
            continue
        if 'content_sha256' in frame:
            for item in frame.dropna(subset=['content_sha256']).to_dict('records'):
                identities.setdefault(item['content_sha256'], set()).add(
                    (item['repo_name'], int(item['pr_number']), item['file_path']))
    for file in ROOT.glob('circuit_state_*.json'):
        events = json.loads(file.read_bytes())
        if isinstance(events, dict):
            events = events.get('window', [])
        for item in events:
            if isinstance(item, dict) and all(k in item for k in ('hash', 'repo', 'pr', 'path')):
                identities.setdefault(item['hash'], set()).add(
                    (item['repo'], int(item['pr']), item['path']))
    cohort = pd.read_csv(outcomes)
    unknown = cohort[cohort.test_added_content_verified.isna()]
    rows = []
    for number, attempt in enumerate(attempts, start=82):
        key = attempt['task']
        record = json.loads(records[key].read_bytes())
        digest = record['content_sha256']
        raw_source = (OUT / 'content' / (digest + '.txt')).read_bytes()
        assert sha256(raw_source) == digest
        text = raw_source.decode('utf-8-sig')
        diag = record.get('diagnostic', {})
        finish = record.get('finish_reason', diag.get('finish_reason'))
        supplied = diag.get('raw_output')
        classification = json.loads(supplied)['classification'] if supplied else record['classification']
        accepted = record['status'] == 'validated'
        recovered = False
        current_error = None
        if accepted:
            grok.validate_cached_classification(record, text)
        elif supplied:
            safe, _ = grok.sanitize(text)
            assert safe is not None and sha256(safe.encode()) == diag['sanitized_input_sha256']
            try:
                parsed = grok.validate_output(supplied, safe, complete=diag['complete_input'])
            except ValueError as exc:
                current_error = str(exc)
            else:
                assert key == RECOVERY and finish == 'REASON_STOP' and diag['complete_input']
                assert grok.validate_output(supplied, text) == parsed
                refs = json.loads(supplied)['evidence']
                value = {**record, **parsed.model_dump(), 'status': 'validated',
                         'complete_input': True, 'evidence_references': refs,
                         'offline_revalidation': {'rule': 'DuckDB C++ extension entry declaration',
                                                  'original_cache_key': key}}
                grok.validate_cached_classification(value, text)
                folder = CACHE / 'offline_revalidated'
                folder.mkdir(exist_ok=True)
                write_json(folder / (key + '.json'), value, immutable=True)
                recovered = True
        matches = sorted(identities[digest])
        for repo, pr, path in matches:
            rows.append({'attempt': number,
                         'task': key, 'repo_name': repo, 'pr_number': pr, 'file_path': path,
                         'api_completed': finish == 'REASON_STOP' and 'usage' in attempt,
                         'classification': classification, 'original_accepted': accepted,
                         'original_error': diag.get('validation_message'),
                         'offline_recovered': recovered, 'current_error': current_error,
                         'deterministic_result': (classify(text, path)['classification']
                                                  if path.endswith('/.npmrc') else None),
                         'reported_cost_usd': attempt.get('reported_cost_usd')})
    groups = full_cohort.groups()
    frontier = audit_pending(unknown, cohort, groups, Resolver(dry_run=True))
    frontier[['next_step', 'uncached_model_files', 'other_unresolved_items']] = pd.DataFrame(
        [classify_frontier(row) for row in frontier.itertuples()], index=frontier.index)
    frontier['one_model_file_only'] = frontier.next_step.eq('model_only') & frontier.uncached_model_files.eq(1)
    frontier.sort_values(['one_model_file_only', 'uncached_model_files'],
                         ascending=[False, True]).to_csv(REPORT / 'unknown_frontier.csv', index=False)
    lookup = frontier.set_index(KEY)
    replay_keys = frontier.loc[frontier.next_step.eq('offline_cache_or_deterministic'), KEY]
    replay_input = unknown.merge(replay_keys, on=KEY, validate='one_to_one')
    if not replay_input.empty:
        scale100.DEST = REPORT / 'offline_replay'
        (scale100.DEST / 'checkpoints').mkdir(parents=True, exist_ok=True)
        replay, evidence, pending = scale100.run_rows(
            replay_input, Resolver(dry_run=True), fetch=False, groups=groups)
        assert not pending
        replay.to_csv(REPORT / 'offline_replay_outcomes.csv', index=False)
        evidence.to_csv(REPORT / 'offline_replay_evidence.csv', index=False)
    for row in rows:
        parent = lookup.loc[(row['repo_name'], row['pr_number'])]
        pending = [d for d in json.loads(parent.details)
                   if not isinstance(d, dict) or d.get('path') != row['file_path']]
        row.update(parent_next_step=parent.next_step, other_pending_items=len(pending),
                   negative_file_alone_could_resolve=not pending and parent.next_step not in {
                       'github_acquisition', 'github_reconciliation'})
    pd.DataFrame(rows).to_csv(REPORT / 'attempts.csv', index=False)
    summary = {
        'unknown': len(frontier), 'next_steps': frontier.next_step.value_counts().to_dict(),
        'states': frontier.verification_state.value_counts().to_dict(),
        'one_model_file_only': int(frontier.one_model_file_only.sum()),
        'model_only_file_counts': frontier.loc[frontier.next_step.eq('model_only'),
                                               'uncached_model_files'].value_counts().sort_index().to_dict(),
        'tranche_reported_cost_usd': sum(a['reported_cost_usd'] for a in attempts),
    }
    write_json(REPORT / 'summary.json', summary)
    assert all(file_hash(p) == h for p, h in hashes.items())
    protect_prior()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
