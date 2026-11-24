import json

import pandas as pd
import pytest

import grok
from audit_batch6_quality import RECOVERY
from common import CACHE, OUT, sha256
from detector import classify
from full_cohort import prioritize_remaining


def test_duckdb_extension_entry_is_a_real_non_test_declaration():
    record = json.loads((CACHE / 'grok' / f'{RECOVERY}.json').read_bytes())
    digest = record['content_sha256']
    raw = (OUT / 'content' / f'{digest}.txt').read_bytes()
    assert sha256(raw) == digest
    source = raw.decode('utf-8-sig')
    value = json.loads(record['diagnostic']['raw_output'])
    assert grok.validate_output(value, source).classification == 'not_test'
    line = 'DUCKDB_CPP_EXTENSION_ENTRY(mssql, loader) {'
    for replacement in [f'// {line}', 'DUCKDB_CPP_EXTENSION_ENTRY(mssql, loader);',
                        f'const char *s = "{line}";']:
        with pytest.raises(ValueError):
            grok.validate_output(value, source.replace(line, replacement))
    commented = source.replace('extern "C" {', '/*').rstrip() + '\n*/'
    with pytest.raises(ValueError):
        grok.validate_output(value, commented)


def test_one_remaining_model_file_with_no_other_blockers_is_first():
    sample = pd.DataFrame({'repo_name': ['repo'] * 3, 'pr_number': [1, 2, 3]})
    missing = {'path': 'model.cpp', 'model_status': 'dry_run'}
    unavailable = {'path': 'old.cpp', 'model_status': 'provider_or_validation_failure'}
    states = sample.assign(verification_state='waiting_grok_classification',
                           details=[json.dumps(x) for x in [
                               [missing, unavailable], [missing, missing], [missing]]])
    assert prioritize_remaining(sample, states).pr_number.tolist() == [3, 2, 1]


def test_rejected_npmrc_is_resolved_from_full_source_without_model():
    key = '41f28193d811d33348007ddd8c51f4ba90a877c67f9680daef9ed02486faef46'
    record = json.loads((CACHE / 'grok' / f'{key}.json').read_bytes())
    digest = record['content_sha256']
    raw = (OUT / 'content' / f'{digest}.txt').read_bytes()
    assert sha256(raw) == digest
    source = raw.decode('utf-8-sig')
    with pytest.raises(ValueError, match='declared role'):
        grok.validate_output(record['diagnostic']['raw_output'], source)
    assert classify(source, 'website/web/.npmrc')['classification'] == 'not_test'
    assert classify(source + '\nassert_test()', '.npmrc')['classification'] == 'uncertain'
    assert classify(source, '.npmrc', complete=False)['classification'] == 'uncertain'
