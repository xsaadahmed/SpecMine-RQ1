import json
import shutil

import pytest

import grok
from common import CACHE, OUT, sha256
from detector import classify


@pytest.mark.skipif(not shutil.which('pwsh'), reason='PowerShell parser unavailable')
def test_actual_rejected_powershell_response_stays_rejected_but_static_test_is_proven():
    key = '081d38852ee308ed48b498d59f4758f76591a63301562e440185b3b9ccb8fef7'
    record = json.loads((CACHE / 'grok' / f'{key}.json').read_bytes())
    digest = record['content_sha256']
    raw = (OUT / 'content' / f'{digest}.txt').read_bytes()
    assert sha256(raw) == digest
    source = raw.decode('utf-8-sig')
    with pytest.raises(ValueError, match='assertion role'):
        grok.validate_output(record['diagnostic']['raw_output'], source)
    path = 'tests/integration/validator-parallelization.tests.ps1'
    result = classify(source, path)
    assert result['classification'] == 'automated_test'
    assert {e['line'] for e in result['evidence']} >= {19, 26, 32, 38}
    for modified in (source.replace('exit 1', 'exit 0'),
                     source.replace('# Test ', '# Setup '),
                     '@\'\n' + source + '\n\'@'):
        assert classify(modified, path)['classification'] == 'uncertain'
    assert classify(source, path, complete=False)['classification'] == 'uncertain'
