"""One bounded evaluation of the revised evidence request, from pinned cached files."""
import argparse
import json
import os

import pandas as pd
import portalocker

import grok
import scale100
from common import CACHE, HERE, KEY, OUT, protect_prior, sha256, write_json
from progress_audit import audit_pending
from storage import Store, metadata_request

NAME = 'evidence_v5_trial'
CASES = (
    ('strelov1/freehire', 410, 'web/src/lib/components/CompanyInfoCard.svelte',
     '89be45567297005a0d7e65da18a670dacc5906c58ec07c619c62d90780526aa5', 'not_test'),
    ('litara-app/litara', 55, 'scripts/run-android.ps1',
     '172f745a3fd3079ddc2f2cbe8473ee5a37e033289b1d87a9fe238a9ac6589f25', 'not_test'),
    ('rustyrazorblade/easy-db-lab', 663,
     'src/test/kotlin/com/rustyrazorblade/easydblab/commands/kit/KitSqlCommandTest.kt',
     '81e4ec1da91df5694a39dbffd589e745333674c368d6fec2a70cb3427969fc3d', 'automated_test'),
)


def source_for(case):
    repo, number, path, digest, _ = case
    store = Store()
    metadata = store.data(metadata_request(repo, number))
    files, complete, _, _ = store.files(repo, number)
    if not metadata or not complete:
        raise RuntimeError('Trial requires the complete pinned diff')
    file = next((f for f in files if f['filename'] == path and f['status'] == 'added'), None)
    if not file:
        raise RuntimeError('Trial file is not in the pinned added-file list')
    text, provenance, _ = store.content(repo, metadata['head_sha'], path, file['sha'])
    if text is None or provenance.get('content_sha256') != digest:
        raise RuntimeError('Trial source hash mismatch')
    return text, provenance


def verified_decision(case, attempts, folder):
    key = grok.cache_key(case[3], grok.EVIDENCE_V5)
    rows = [row for row in attempts if row['task'] == key]
    cache = folder / 'grok' / (key + '.json')
    if (len(rows) != 1 or not cache.is_file() or rows[0].get('status') != 'completed'
            or 'reported_cost_usd' not in rows[0]):
        return False
    decision = json.loads(cache.read_bytes())
    if (decision.get('cache_key') != key or decision.get('content_sha256') != case[3]
            or decision.get('prompt_version') != grok.EVIDENCE_V5
            or decision.get('prompt_sha256') != sha256(grok.SYSTEM_V5.encode())
            or decision.get('model') != grok.MODEL or decision.get('reasoning_effort') != grok.REASONING
            or decision.get('reported_cost_usd') != rows[0]['reported_cost_usd']
            or decision.get('finish_reason') != 'REASON_STOP'
            or decision.get('status') != 'validated' or decision.get('needs_review')
            or decision.get('classification') != case[4] or not decision.get('complete_input')):
        return False
    text, _ = source_for(case)
    grok.validate_cached_classification(decision, text)
    return True


def approved(root, attempts):
    receipt = root / NAME / 'result.json'
    if not receipt.is_file():
        return False
    data = json.loads(receipt.read_bytes())
    expected = [{'repo_name': repo, 'pr_number': number,
                 'outcome': int(label == 'automated_test')}
                for repo, number, _, _, label in CASES]
    return (data.get('passed') is True and data.get('outcomes') == expected
            and all(verified_decision(case, attempts, receipt.parent) for case in CASES))


def admit_trial_cache(root, attempts):
    from cohort_overlay import reference_trial_required
    if reference_trial_required(root):
        raise RuntimeError('Evidence v5 trial retired; use independent_review.py')
    if not approved(root, attempts):
        raise RuntimeError('Evidence v5 requires three successful controlled validation cases')
    for case in CASES:
        name = grok.cache_key(case[3], grok.EVIDENCE_V5) + '.json'
        record = json.loads((root / NAME / 'grok' / name).read_bytes())
        write_json(CACHE / 'grok' / name, record, immutable=True)


def print_trial_status(folder):
    result_path = folder / 'result.json'
    if not result_path.is_file():
        print('No completed trial result. Overnight paid dispatch stays locked.')
        return
    result = json.loads(result_path.read_bytes())
    if result.get('passed') is True:
        print('Trial recorded a pass. Overnight will verify its evidence and ledger.')
        return
    failed_at = result['failed_at']
    repo, number, path, digest, _ = CASES[failed_at - 1]
    print(f'Trial stopped at case {failed_at}, {repo} #{number}, {path}.')
    record_path = folder / 'grok' / (grok.cache_key(digest, grok.EVIDENCE_V5) + '.json')
    if record_path.is_file():
        record = json.loads(record_path.read_bytes())
        diagnostic = record.get('diagnostic') or {}
        reason = (diagnostic.get('validation_message') or diagnostic.get('transport_status')
                  or 'Expected a complete PR outcome backed by a validated response and matching ledger entry')
        print(f'Saved diagnostic: {reason}')
    else:
        print('No model response was saved for this case.')
    print('Overnight paid dispatch stays locked.')


class TrialBudget(scale100.ScalingBudget):
    allowed_key = None

    def reserve(self, bound, task):
        if task != self.allowed_key or any(row['task'] == task for row in self.state['attempts']):
            raise RuntimeError('scaling_preflight_not_satisfied')
        return super().reserve(bound, task)


def main():
    import full_cohort

    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--live', action='store_true')
    modes.add_argument('--status', action='store_true', help='Read the saved trial result without any API calls')
    args = parser.parse_args()
    root = full_cohort.DEST
    folder = root / NAME
    if args.status:
        print_trial_status(folder)
        return
    from cohort_overlay import reference_trial_required
    if reference_trial_required(root):
        print('Evidence v5 trial retired. Use independent_review.py. Historical records are preserved.')
        return
    budget = TrialBudget(max_spend=7, max_requests=1000)
    attempts = budget.state['attempts']
    budget.max_requests = min(1000, len(attempts) + len(CASES))
    keys = {grok.cache_key(case[3], grok.EVIDENCE_V5) for case in CASES}
    if args.live and ((folder / 'started.json').exists()
                      or any(row['task'] in keys for row in attempts)):
        parser.error('This trial has already run. Use --status to inspect the saved result.')
    if args.live and not os.environ.get('XAI_API_KEY','').strip():
        parser.error('XAI_API_KEY is required for live validation')
    protect_prior()
    cohort = pd.read_csv(root / 'current_main_outcomes.csv')
    target = pd.DataFrame([case[:2] for case in CASES], columns=KEY)
    selected = target.merge(cohort, on=KEY, validate='one_to_one', how='left')
    if not selected.test_added_content_verified.isna().all():
        parser.error('Trial inputs must still be unresolved')
    groups = full_cohort.groups()
    state = audit_pending(selected, selected, groups, scale100.Resolver(dry_run=True))
    for case, row in zip(CASES, state.itertuples(), strict=True):
        text, _ = source_for(case)
        safe, _ = grok.sanitize(text)
        details = json.loads(row.details)
        if (safe is None or safe != text or len(safe.encode()) > grok.MAX_BYTES
                or row.verification_state != 'waiting_grok_classification'
                or details != [{'path': case[2], 'model_status': 'dry_run', 'diagnostic': None}]):
            raise RuntimeError('Trial candidate is no longer exactly one fresh full-source decision')
    print(state[KEY + ['verification_state']].to_string(index=False))
    if not args.live:
        return
    resolver = scale100.Resolver(dry_run=False, budget=budget, evidence_v5=True,
                                 circuit_path=full_cohort.evidence_v5_circuit_path(root),
                                 fallback_on_quality=True, cache_dir=folder/'grok')
    if resolver.transport_blocked or resolver.model_disabled:
        parser.error('An existing transport or v5 quality breaker blocks this trial')
    folder.mkdir(exist_ok=True)
    (folder / 'checkpoints').mkdir(exist_ok=True)
    (folder / 'grok').mkdir(exist_ok=True)
    write_json(folder / 'started.json', {'version': grok.EVIDENCE_V5, 'attempts_before': len(attempts),
                                       'cases': CASES}, immutable=True)
    scale100.DEST = folder
    results = []
    for index, case in enumerate(CASES):
        budget.allowed_key = grok.cache_key(case[3], grok.EVIDENCE_V5)
        row, audit, frontier = scale100.run_rows(
            selected.iloc[[index]], resolver, fetch=False, groups=groups)
        audit.to_csv(folder / f'audit_{index+1}.csv', index=False)
        outcome = row.iloc[0].test_added_content_verified
        if (frontier or pd.isna(outcome) or int(outcome) != int(case[4]=='automated_test')
                or not verified_decision(case, attempts, folder)):
            write_json(folder / 'result.json', {'passed': False, 'failed_at': index + 1,
                                                'outcomes': results}, immutable=True)
            print_trial_status(folder)
            return
        results.append({'repo_name':case[0], 'pr_number':case[1], 'outcome':int(outcome)})
    protect_prior()
    write_json(folder / 'result.json', {'passed': True, 'outcomes': results}, immutable=True)
    print('Evidence v5 passed. All three complete PR outcomes matched their source review.')


if __name__ == '__main__':
    with portalocker.Lock(str(HERE / '.run.lock'), timeout=.1):
        main()
