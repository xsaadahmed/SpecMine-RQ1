"""Evidence/invariant checks; no assumption of independent human reference labels."""
import json

import pandas as pd

from common import CACHE,HIST,OUT,ROOT,file_hash,protect_prior,write_json
from detector import eligible
from storage import git_blob_sha


def validate():
    n=protect_prior()
    files=pd.read_csv(OUT/'file_classification_results.csv')
    assert len(files)==56 and not files.review_id.duplicated().any()
    assert files.independent_human_reference.eq(False).all()
    comparisons={}
    for scope,expected in [('pilot',40),('main',3186)]:
        p=pd.read_csv(OUT/f'{scope}_pr_outcomes.csv')
        audit=pd.read_csv(OUT/f'{scope}_inspection_audit.csv')
        assert len(p)==expected and not p.duplicated(['repo_name','pr_number']).any()
        assert p.test_added_content_verified.dropna().isin([0,1]).all()
        assert not audit.duplicated(['repo_name','pr_number','file_path']).any()
        for r in p.itertuples():
            sub=audit[audit.repo_name.eq(r.repo_name)&audit.pr_number.eq(r.pr_number)]
            assert int(sub.examined.eq(True).sum())==r.n_files_inspected
            if pd.isna(r.test_added_content_verified):continue
            if r.test_added_content_verified==0:
                assert r.inspection_complete and r.file_list_complete
                assert r.n_files_inspected==r.n_eligible_added_files
                assert not sub.classification.isin(['uncertain','automated_test']).any()
            else:
                supporting=sub[sub.file_path.eq(r.confirmed_file_path)]
                assert len(supporting)==1 and supporting.classification.eq('automated_test').all()
                raw=(ROOT/supporting.content_reference.iloc[0]).read_bytes()
                assert file_hash(ROOT/supporting.content_reference.iloc[0])==r.file_content_hash
                assert git_blob_sha(raw)==supporting.blob_sha.iloc[0]
                assert str(r.pinned_commit_sha) in supporting.pinned_url.iloc[0]
                assert eligible(r.confirmed_file_path)
        comparisons[scope]={'confirmed':int(p.test_added_content_verified.eq(1).sum()),'negative':int(p.test_added_content_verified.eq(0).sum()),'unknown':int(p.test_added_content_verified.isna().sum())}
    usage=json.loads((OUT/'api_usage_report.json').read_text())
    assert usage['charged_or_reserved_usd']<=3+1e-9
    assert usage['requests_without_key']==0,'No paid dispatch may lack a key'
    human=pd.read_csv(HIST/'outputs/human_review.csv')
    assert human.manual_is_automated_test.isna().all(),'Independent labels changed; evaluate their provenance separately'
    write_json(OUT/'validation_results.json',{'status':'passed','prior_files_hash_identical':n,'file_evaluation_n':len(files),'outcomes':comparisons,'actual_xai_requests':usage['requests_attempted'],'paid_cost_usd':usage['reported_cost_usd'],'accuracy_precision_recall':'unavailable_without_independent_reference_labels','checks':['prior baseline/data/pilot/review hashes','one observation per PR','all positives have pinned added-file source evidence','zeros require exhaustive complete-source inspection','unknowns remain missing','content SHA-256 and Git blob hashes','no paid requests without XAI_API_KEY']})
    return n
