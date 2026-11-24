import base64
import json

import pytest

from common import CACHE
from pipeline import search_pr
from storage import Store, content_request, git_blob_sha
import quarantine_path_reference as registration

REPO = '21-DOT-DEV/swift-secp256k1'
HEAD = '7db2793e98ee1abc4281809591793f29d8aea3e2'
PATH = 'Projects/Sources/libsecp256k1Tests/precomputed_ecmult.c'
TARGET = '../../../Vendor/secp256k1/src/precomputed_ecmult.c'
EXPECTED = '2f66e8fdbf3eecb385d601cc472f19925395a8ae'
ACTUAL = '7778983522578679eacec72e2abf8ac4044b85f0'


def test_actual_second_incident_has_independent_object_identity():
    req = content_request(REPO, HEAD, PATH)
    record = Store().record(req)
    assert record['request'] == req
    assert record['data']['sha'] == EXPECTED == git_blob_sha(TARGET.encode())
    raw = base64.b64decode(record['data']['content'])
    assert git_blob_sha(raw) == ACTUAL != EXPECTED
    assert len(raw) == 1048576


def test_register_actual_incident_offline_is_immutable_and_not_source(tmp_path, monkeypatch):
    store = Store()
    monkeypatch.setattr(registration, 'CACHE', tmp_path)
    report = tmp_path / 'report.json'
    proof = registration.register_reference(REPO, 945, PATH, TARGET, report, store)
    assert proof['expected_blob_sha'] == EXPECTED
    assert proof['computed_response_blob_sha'] == ACTUAL
    assert proof['file_mode'] is None  # Do not invent Git mode evidence.
    assert proof['classification'] == 'unresolved'
    assert registration.register_reference(REPO, 945, PATH, TARGET, report, store) == proof
    import storage
    monkeypatch.setattr(storage, 'CACHE', tmp_path)
    text, diagnostic, pending = store.content(REPO, HEAD, PATH, EXPECTED)
    assert text is None and pending is None
    assert diagnostic['status'] == 'quarantined_path_reference_contents_response'


@pytest.mark.parametrize('target', ['../fabricated.c', '/absolute.c', '../x\n', '../x\0', ''])
def test_bad_reference_cannot_register(tmp_path, monkeypatch, target):
    monkeypatch.setattr(registration, 'CACHE', tmp_path)
    with pytest.raises(ValueError):
        registration.register_reference(REPO, 945, PATH, target, tmp_path/'report.json')
    assert not (tmp_path/'report.json').exists()


def test_no_proof_retains_integrity_stop(tmp_path, monkeypatch):
    import storage
    store = Store()
    store.record(content_request(REPO, HEAD, PATH))
    monkeypatch.setattr(storage, 'CACHE', tmp_path)
    text, diagnostic, pending = store.content(REPO, HEAD, PATH, EXPECTED)
    assert text is None and pending is None and diagnostic['integrity_error']


def test_quarantine_continues_search_but_cannot_support_negative(tmp_path, monkeypatch):
    import storage
    store = Store()
    monkeypatch.setattr(registration, 'CACHE', tmp_path)
    registration.register_reference(REPO, 945, PATH, TARGET, tmp_path/'report.json', store)
    monkeypatch.setattr(storage, 'CACHE', tmp_path)
    files = [{'filename': PATH, 'status': 'added', 'sha': EXPECTED}]
    def fetch(f):
        if f['filename'] == PATH:
            return store.content(REPO, HEAD, PATH, EXPECTED)
        return 'test body', {'commit_sha': HEAD, 'content_sha256': 'known-fixture'}, None
    def classify(text, f, provenance):
        assert f['filename'] != PATH
        return {'classification': 'automated_test', 'has_executable_tests': True,
                'needs_review': False, 'method': 'deterministic', 'evidence': ['test body']}
    result, audit, _ = search_pr(files, fetch, classify)
    assert result['test_added_content_verified'] is None
    assert not result['inspection_complete'] and not audit[0]['examined']
    files += [{'filename': 'z_regular.c', 'status': 'added'},
              {'filename': 'zz_never_needed.c', 'status': 'added'}]
    result, audit, _ = search_pr(files, fetch, classify)
    assert result['test_added_content_verified'] == 1
    assert result['confirmed_file_path'] == 'z_regular.c'
    assert len(audit) == 2 and result['early_exit']


def test_conflicting_pr_metadata_cannot_register(tmp_path, monkeypatch):
    store = Store()
    req = content_request(REPO, HEAD, PATH)
    record = json.loads(json.dumps(store.record(req)))
    record['data']['sha'] = '0'*40
    store.memory[req['id']] = record
    monkeypatch.setattr(registration, 'CACHE', tmp_path)
    with pytest.raises(ValueError, match='metadata SHA disagree'):
        registration.register_reference(REPO, 945, PATH, TARGET, tmp_path/'report.json', store)
    assert not (tmp_path/'report.json').exists()
