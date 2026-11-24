import pytest
import pandas as pd
from evaluate_annotations import evaluate


def test_assistant_labels_cannot_unlock_metrics(tmp_path):
    path=tmp_path/'assistant.csv'
    pd.DataFrame([dict(review_id='F1',adjudicated_label=1,reviewer_id='Codex assistant',annotation_origin='assistant',annotation_timestamp='2026-11-02',retrieval_status='verified')]).to_csv(path,index=False)
    with pytest.raises(AssertionError):evaluate(path,attested=True)
