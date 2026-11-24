import json

import pytest

import ai_assisted as pipeline
import codex_source_review as direct


def test_exact_evidence_rejects_missing_or_repeated_coordinates():
    text = 'first line\nsecond line'
    assert direct.exact_evidence(text,((1,'first'),(2,'second')))[1]['line']==2
    with pytest.raises(ValueError,match='missing'):
        direct.exact_evidence(text,((1,'second'),(2,'second')))
    with pytest.raises(ValueError,match='distinct'):
        direct.exact_evidence(text,((1,'first'),(1,'line')))


@pytest.mark.parametrize('version',[
    'codex_source_review_v1','codex_source_review_v2','codex_source_review_v3',
    'codex_source_review_v4','codex_source_review_v5','codex_source_review_v6',
    'codex_source_review_v7','codex_source_review_v8','codex_source_review_v9',
    'codex_source_review_v10','codex_source_review_v11','codex_source_review_v12','codex_source_review_v13',
    'codex_source_review_v14','codex_source_review_v15','codex_source_review_v16',
])
def test_direct_reviews_have_source_proofs_and_complete_negative_audits(version):
    folder = pipeline.DEST/version
    manifest = json.loads((folder/'manifest.json').read_bytes())
    assert manifest['human_reviewed'] is manifest['grok_used'] is False
    results = pipeline.published_delta().set_index(pipeline.KEY)
    for item in manifest['items']:
        key = item['repo_name'],item['pr_number']
        is_test = item['classification']=='automated_test'
        direct.exact_evidence(
            pipeline.review.source(item),item['anchors'],single_line_negative=not is_test)
        outcome = results.loc[key]
        assert int(outcome[pipeline.overlay.LABEL])==int(is_test)
        if not is_test:
            assert outcome['inspection_complete']


def test_single_line_negative_requires_entire_source_line():
    text = 'engine-strict=true\n'
    anchor = ((1,'engine-strict=true'),)
    assert direct.exact_evidence(text,anchor,single_line_negative=True)[0]['line']==1
    with pytest.raises(ValueError,match='distinct'):
        direct.exact_evidence(text,((1,'engine-strict'),),single_line_negative=True)
    with pytest.raises(ValueError,match='distinct'):
        direct.exact_evidence(text,anchor)
