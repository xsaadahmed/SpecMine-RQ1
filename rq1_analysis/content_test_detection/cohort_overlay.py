"""Admit the pinned v1 delta without rewriting any per-batch history."""
import json

import pandas as pd

from common import KEY, file_hash, protect_prior, write_json

VERSION = 'final_verification_v1'
LABEL = 'test_added_content_verified'
SNAPSHOTS = ('current_main_outcomes.csv', 'current_unknown_queue.csv', 'progress.json')
PROOFS = ('verified_delta.csv', 'verified_delta_evidence.csv', 'verified_cohort.csv', 'input_hashes.json')


def installation(root):
    return root / VERSION / 'runner_integration'


def installed(root):
    return (installation(root) / 'admitted.json').is_file()


def reference_trial_required(root):
    return (root / VERSION / 'verified_delta.csv').is_file()


def read_delta(root):
    if not installed(root):
        return pd.DataFrame(columns=KEY + [LABEL])
    proof = root / VERSION
    folder = installation(root)
    receipt = json.loads((folder / 'admitted.json').read_bytes())
    paths = [proof / name for name in PROOFS] + [folder / name for name in SNAPSHOTS]
    if (receipt['version'] != VERSION or
            receipt['hashes'] != {p.name: file_hash(p) for p in paths}):
        raise RuntimeError('Versioned cohort admission integrity mismatch')
    return pd.read_csv(proof / 'verified_delta.csv')


def apply_delta(frame, delta, *, require_membership=False):
    if frame.duplicated(KEY).any() or delta.duplicated(KEY).any():
        raise RuntimeError('Duplicate study identifier in cohort overlay')
    if not delta[LABEL].isin([0, 1]).all():
        raise RuntimeError('A versioned delta must contain resolved outcomes only')
    output = frame.set_index(KEY).copy()
    for row in delta.to_dict('records'):
        key = tuple(row[col] for col in KEY)
        if key not in output.index:
            if require_membership:
                raise RuntimeError('Versioned PR missing from study cohort')
            continue
        old = output.at[key, LABEL]
        if pd.notna(old):
            if old != row[LABEL]:
                raise RuntimeError(f'Conflicting verified labels for {key}')
            continue
        for col in output.columns:
            if col in row:
                output.at[key, col] = row[col]
    return output.reset_index()


def prefrozen_main(root):
    folder = installation(root)
    path = folder / SNAPSHOTS[0]
    return path if path.exists() else root / SNAPSHOTS[0]


def counts(frame):
    labels = frame[LABEL]
    return {'positive': int(labels.eq(1).sum()), 'negative': int(labels.eq(0).sum()),
            'unknown': int(labels.isna().sum())}


def atomic_csv(path, frame):
    temporary = path.with_suffix('.csv.tmp')
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def integrate(root):
    from full_cohort import groups
    from final_verify import verify_pr
    from storage import Store

    proof = root / VERSION
    folder = installation(root)
    current = pd.read_csv(root / SNAPSHOTS[0])
    if installed(root):
        delta = read_delta(root)
    else:
        expected = json.loads((proof / 'input_hashes.json').read_bytes())
        expected = {key.replace('\\', '/'): digest for key, digest in expected.items()}
        original_path = prefrozen_main(root)
        if file_hash(original_path) != expected['full_cohort/current_main_outcomes.csv']:
            raise RuntimeError('Current cohort does not match the original v1 input')
        before = pd.read_csv(original_path)
        delta = pd.read_csv(proof / 'verified_delta.csv')
        versioned = pd.read_csv(proof / 'verified_cohort.csv')
        merged = apply_delta(before, delta, require_membership=True)
        pd.testing.assert_series_equal(merged.set_index(KEY)[LABEL],
                                       versioned.set_index(KEY)[LABEL])
        if (len(delta) != int(before[LABEL].isna().sum() - merged[LABEL].isna().sum())
                or len(before) != 3186):
            raise RuntimeError('Delta is not a strict extension of the versioned cohort')
        evidence = pd.read_csv(proof / 'verified_delta_evidence.csv')
        store, frozen_groups = Store(), groups()
        for row in delta.to_dict('records'):
            verify_pr(row, evidence, store, frozen_groups)
        protected = protect_prior()
        folder.mkdir(exist_ok=True)
        for name in SNAPSHOTS:
            archive = folder / name
            if not archive.exists():
                with archive.open('xb') as stream:
                    stream.write((root / name).read_bytes())
            if file_hash(archive) != file_hash(root / name):
                raise RuntimeError(f'Archived publication differs from original: {name}')
        paths = [proof / name for name in PROOFS] + [folder / name for name in SNAPSHOTS]
        write_json(folder / 'admitted.json', {
            'version': VERSION, 'hashes': {p.name: file_hash(p) for p in paths},
            'before': counts(before), 'delta': counts(delta), 'after': counts(merged),
            'pinned_prs_reverified': len(delta), 'prior_files_checked': protected,
        }, immutable=True)
    merged = apply_delta(current, delta, require_membership=True)
    if not merged.equals(current):
        atomic_csv(root / SNAPSHOTS[0], merged)
    pending = merged[merged[LABEL].isna()]
    if len(pd.read_csv(root / SNAPSHOTS[1])) != len(pending):
        atomic_csv(root / SNAPSHOTS[1], pending)
    progress = json.loads((root / SNAPSHOTS[2]).read_bytes())
    if progress['main'] != counts(merged):
        progress.update(main=counts(merged), cohort_overlay=VERSION)
        write_json(root / SNAPSHOTS[2], progress)
    return counts(merged)


if __name__ == '__main__':
    import portalocker
    from common import HERE, OUT

    with portalocker.Lock(str(HERE / '.run.lock'), timeout=.1):
        print(json.dumps(integrate(OUT / 'full_cohort'), indent=2))
