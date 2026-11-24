import json

import pytest

import grok
from common import CACHE, OUT, sha256


def test_tinymist_saved_response_requires_asserting_suite_callbacks():
    key = '7b416242e213267fa77b50a114dc13045f1ed5e58fd1f4cba2aae84ccb43e5b5'
    archived = json.loads((CACHE / 'grok' / f'{key}.json').read_bytes())
    digest = archived['content_sha256']
    raw = (OUT / 'content' / f'{digest}.txt').read_bytes()
    assert sha256(raw) == digest
    source = raw.decode('utf-8-sig')
    response = archived['diagnostic']['raw_output']
    assert grok.validate_output(response, source).classification == 'automated_test'
    assert grok.workspace_test_references(source)[48] >= {54, 68}
    for replacement in [source.replace('suite.addTest(', 'fake.addTest('),
                        source.replace('.to.be.equal(', '.somethingElse(')
                              .replace('.to.include(', '.somethingElse('),
                        source.replace('async (suite) =>', 'async (fake) =>')]:
        with pytest.raises(ValueError):
            grok.validate_output(response, replacement)
