"""Withhold accuracy metrics until a human-attested reference file is supplied."""
import argparse

import pandas as pd

from hv_common import OUT, write_json


def evaluate(path=None, attested=False):
    result={"status":"awaiting_trustworthy_reference_annotations","precision":None,"recall":None}
    if path is None or not attested:
        result["reason"]="Supply completed independent human annotations and explicitly attest to their provenance. Blank forms and old assistant labels do not qualify."
        write_json(OUT / "annotation_readiness.json",result)
        print(result["reason"])
        return result
    a=pd.read_csv(path)
    needed=["review_id","adjudicated_label","reviewer_id","annotation_origin","annotation_timestamp","retrieval_status"]
    assert set(needed)<=set(a.columns),"Missing provenance/adjudication columns"
    a=a[a.retrieval_status.eq("verified")].copy()
    assert len(a)>0 and not a.review_id.duplicated().any()
    assert a.annotation_origin.eq("independent_human").all(),"Annotations are not human-attested independent references"
    assert a.reviewer_id.notna().all() and a.annotation_timestamp.notna().all()
    assert not a.reviewer_id.str.contains(r"codex|assistant|chatgpt",case=False,regex=True).any()
    assert a.adjudicated_label.isin([0,1]).all(),"Adjudicate all retrieved cases before scoring"
    plan=pd.read_csv(OUT / "review_sample_plan.csv")
    available=pd.read_csv(OUT / "review_content_retrieval.csv")
    expected=set(available.loc[available.retrieval_status.eq("verified"),"review_id"])
    assert set(a.review_id)==expected,"Reference sample differs or has selective missing labels"
    joined=a.merge(plan[["review_id","is_test","design_weight"]],on="review_id",validate="one_to_one")
    pred=joined.is_test.astype(bool);true=joined.adjudicated_label.eq(1);w=joined.design_weight
    tp=float(w[pred & true].sum());fp=float(w[pred & ~true].sum());fn=float(w[~pred & true].sum());tn=float(w[~pred & ~true].sum())
    result.update(status="human_attested_reference_scored",n=len(joined),weighted_tp=tp,weighted_fp=fp,weighted_fn=fn,weighted_tn=tn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,reference_provenance="human attestation provided; independence cannot be certified automatically",scope="Only the sampled pilot-file frame; inverse file-sampling weights; inaccessible files may bias results; no full-corpus claim")
    from hv_common import digest
    from pathlib import Path
    write_json(OUT / ("annotation_evaluation_"+digest(Path(path))[:16]+".json"),result,immutable=True)
    print(result)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--annotations");p.add_argument("--human-reference-attested",action="store_true")
    args=p.parse_args();evaluate(args.annotations,args.human_reference_attested)
