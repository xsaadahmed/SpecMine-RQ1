"""Offline registration of exact, hash-proven Contents/path-reference anomalies.

This is not automatic symlink detection. A reviewed relative target is required;
its literal bytes must reproduce the expected Git object identity independently.
No returned target content is accepted. Unknown mismatches remain hard failures.
"""
import argparse
import base64
import re
from pathlib import PurePosixPath, Path

from common import CACHE, sha256, write_json
from storage import Store, metadata_request, content_request, git_blob_sha


def register_reference(repo, number, path, target, report, store=None):
    """Verify pinned metadata and exact response before writing immutable proof."""
    if (not isinstance(target, str) or not target or len(target.encode()) > 4096
            or any(c in target for c in ('\0', '\n', '\r', '\\'))
            or PurePosixPath(target).is_absolute()):
        raise ValueError('Expected a reviewed, single-line relative path reference')
    store = store or Store()
    metadata = store.data(metadata_request(repo, number))
    files, complete, _, _ = store.files(repo, number)
    if not metadata or not complete:
        raise ValueError('Complete cached PR metadata/file list required')
    head = metadata.get('head_sha', '')
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('Pinned head SHA required')
    matches = [f for f in files if f['filename'] == path]
    if len(matches) != 1 or matches[0]['status'] != 'added':
        raise ValueError('Unique added PR file required')
    expected = matches[0].get('sha')
    if git_blob_sha(target.encode('utf-8')) != expected:
        raise ValueError('Reference bytes do not reproduce PR file Git blob SHA')
    req = content_request(repo, head, path)
    record = store.record(req)
    if not record or not record.get('ok') or record.get('request') != req:
        raise ValueError('Exact successful pinned cached response required')
    data = record['data']
    if data.get('sha') != expected:
        raise ValueError('PR file SHA and Contents metadata SHA disagree')
    if data.get('encoding') == 'base64':
        raw = base64.b64decode(''.join(data['content'].split()), validate=True)
    elif data.get('encoding') == 'utf-8':
        raw = data['content'].encode('utf-8')
    else:
        raise ValueError('Cannot verify returned content encoding')
    actual = git_blob_sha(raw)
    if actual == expected:
        raise ValueError('Response is hash-consistent; quarantine is not justified')
    proof = {
        'proof_version': 'reviewed-relative-reference-v1',
        'request': req, 'pr_number': int(number),
        'expected_blob_sha': expected, 'returned_metadata_sha': data['sha'],
        'computed_response_blob_sha': actual, 'response_sha256': sha256(raw),
        'expected_reference_text': target,
        'expected_reference_git_blob_sha': git_blob_sha(target.encode('utf-8')),
        'decoded_response_bytes': len(raw), 'reported_response_size': data.get('size'),
        'file_mode': None,
        'finding': 'Expected object is a hash-proven path reference. Returned bytes '
                   'do not represent it; consistent with Contents symlink dereferencing. '
                   'Git tree mode and complete target identity not independently verified.',
        'classification': 'unresolved',
    }
    # A separate report preserves the investigation; originals are never rewritten.
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    write_json(report, proof, immutable=True)
    directory = CACHE / 'quarantined_path_references'
    directory.mkdir(exist_ok=True)
    write_json(directory / (req['id'] + '.json'), proof, immutable=True)
    return proof


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True)
    p.add_argument('--pr', required=True, type=int)
    p.add_argument('--path', required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--report', required=True)
    a = p.parse_args()
    proof = register_reference(a.repo, a.pr, a.path, a.target, a.report)
    print('Registered exact hash-proven quarantine:', proof['request']['id'])


if __name__ == '__main__':
    main()
