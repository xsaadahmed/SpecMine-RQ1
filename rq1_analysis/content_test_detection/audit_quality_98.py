"""Recheck the four latest model decisions and evaluate the frontier offline."""
import json

import pandas as pd

import full_cohort
import grok
import scale100
from audit_batch6_quality import classify_frontier
from common import CACHE, KEY, OUT, file_hash, protect_prior, sha256, write_json
from progress_audit import audit_pending


def main():
    root = full_cohort.DEST
    report = root / 'overnight_quality_98'
    report.mkdir(exist_ok=True)
    circuit = full_cohort.quality_circuit_path(root)
    ledger = OUT / 'api_ledger.json'
    outcomes = root / 'current_main_outcomes.csv'
    attempts = json.loads(ledger.read_bytes())['attempts'][94:98]
    assert len(attempts) == 4
    response_paths = [CACHE / 'grok' / (a['task'] + '.json') for a in attempts]
    protected = {p: file_hash(p) for p in [
        ledger, outcomes, circuit, *root.glob('batch_*/sample.csv'), *response_paths]}
    resolver = scale100.Resolver(dry_run=True, circuit_path=circuit)
    decisions = {event['cache_key']: event for event in resolver.recent_results}
    rows = []
    for number, path in enumerate(response_paths, 95):
        record = json.loads(path.read_bytes())
        event = decisions[record['cache_key']]
        digest = record['content_sha256']
        raw = (OUT / 'content' / (digest + '.txt')).read_bytes()
        assert sha256(raw) == digest
        source = raw.decode('utf-8-sig')
        safe, _ = grok.sanitize(source)
        diag = record.get('diagnostic', {})
        validation_error = None
        if record['status'] == 'validated':
            parsed = grok.validate_cached_classification(record, source)
            model_class = parsed.classification
            refs = record['evidence_references']
        else:
            assert sha256(safe.encode()) == diag['sanitized_input_sha256']
            response = json.loads(diag['raw_output'])
            refs = response['evidence']
            model_class = response['classification']
            try:
                grok.validate_output(response, safe, complete=diag['complete_input'])
            except ValueError as exc:
                validation_error = str(exc)
            assert validation_error
        static = full_cohort.engine.hybrid(source, event['path'], digest,
                                           scale100.Resolver(dry_run=True))[0]
        lines = source.splitlines()
        rows.append({'attempt': number, 'repo_name': event['repo'], 'pr_number': event['pr'],
                     'file_path': event['path'], 'model_classification': model_class,
                     'accepted': record['status'] == 'validated', 'validation_error': validation_error,
                     'symbols_exist_on_cited_lines': all(
                         1 <= ref['line'] <= len(lines) and ref['symbol'] in lines[ref['line'] - 1]
                         for ref in refs),
                     'offline_result': static['classification'], 'method': static['method'],
                     'cache_key': record['cache_key'], 'content_sha256': digest})
    pd.DataFrame(rows).to_csv(report / 'attempts.csv', index=False)
    cohort = pd.read_csv(outcomes)
    unknown = cohort.loc[cohort.test_added_content_verified.isna()]
    groups = full_cohort.groups()
    frontier = audit_pending(unknown, cohort, groups, scale100.Resolver(dry_run=True))
    frontier[['next_step', 'uncached_model_files', 'other_unresolved_items']] = pd.DataFrame(
        [classify_frontier(row) for row in frontier.itertuples()], index=frontier.index)
    frontier['one_model_file_only'] = frontier.next_step.eq('model_only') & frontier.uncached_model_files.eq(1)
    frontier.to_csv(report / 'unknown_frontier.csv', index=False)
    ready = frontier.loc[frontier.next_step.eq('offline_cache_or_deterministic'), KEY]
    replay_input = unknown.merge(ready, on=KEY, validate='one_to_one')
    replay_counts = {}
    if len(replay_input):
        scale100.DEST = report / 'offline_replay'
        (scale100.DEST / 'checkpoints').mkdir(parents=True, exist_ok=True)
        replay, evidence, _ = scale100.run_rows(
            replay_input, scale100.Resolver(dry_run=True), fetch=False, groups=groups)
        replay.to_csv(report / 'offline_replay_outcomes.csv', index=False)
        evidence.to_csv(report / 'offline_replay_evidence.csv', index=False)
        replay_counts = replay.test_added_content_verified.value_counts(dropna=False).to_dict()
    assert all(file_hash(p) == digest for p, digest in protected.items())
    summary = {'unknown': len(unknown), 'next_steps': frontier.next_step.value_counts().to_dict(),
               'one_model_file_only': int(frontier.one_model_file_only.sum()), 'replay_outcomes': replay_counts,
               'quality_tripped': resolver.quality_tripped(),
               'window_failures': sum(bool(event['failed']) for event in resolver.recent_results),
               'frozen_files_verified': protect_prior()}
    write_json(report / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
