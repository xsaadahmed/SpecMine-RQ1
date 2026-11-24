"""Frozen content-review sample and blank human annotation forms; no reference labels."""
import argparse
import json

import pandas as pd

from extract import verified_content
from hv_common import BASELINE, KEY, OUT, content_req, data_for, hash_order, pr_req, write_json
from plan import full_list, pilot


def plan_review():
    target=OUT / "review_sample_plan.csv"
    if target.exists():
        print("Using frozen file review sample")
        return
    f=pd.read_parquet(BASELINE / "outputs/intermediate/classified_files.parquet")
    f=f.merge(pilot()[KEY+["pilot_id","tool"]],on=KEY,validate="many_to_one")
    f["sampling_stratum"]=f.tool+"|pred="+f.is_test.astype(int).astype(str)+"|uncertain="+f.test_uncertain.astype(int).astype(str)
    f["selection_hash"]=[hash_order("review|"+r+"|"+str(n)+"|"+path) for r,n,path in zip(f.repo_name,f.pr_number,f.file_path)]
    selected=[]
    strata=[]
    for name,g in f.groupby("sampling_stratum"):
        n=min(8,len(g))
        s=g.sort_values("selection_hash").head(n).copy()
        s["stratum_frame_n"],s["stratum_sample_n"]=len(g),n
        s["inclusion_probability"]=n/len(g)
        s["design_weight"]=len(g)/n
        selected.append(s)
        strata.append({"stratum":name,"frame_n":len(g),"sample_n":n})
    d=pd.concat(selected,ignore_index=True).sort_values(["sampling_stratum","selection_hash"]).reset_index(drop=True)
    d.insert(0,"review_id",[f"F{i:03d}" for i in range(1,len(d)+1)])
    refs=[]
    for r in d.to_dict("records"):
        meta=data_for(pr_req(r["repo_name"],r["pr_number"]))
        files=full_list(r["repo_name"],r["pr_number"],"files")
        exact=[x for x in files or [] if x["filename"]==r["file_path"]]
        renamed=[x for x in files or [] if x.get("previous_filename")==r["file_path"]]
        live=(exact or renamed)
        r.update(commit_sha=None,content_repo=r["repo_name"],content_path=r["file_path"],content_version=None,expected_blob_sha=None,live_status=None)
        if meta and len(live)==1:
            live=live[0]
            r["content_path"]=live["filename"]
            r["live_status"]=live["status"]
            if live["status"]=="removed":
                r["commit_sha"]=meta["base_sha"]
                r["content_version"]="pinned_PR_base_for_removed_file_not_a_temporal_anchor"
            else:
                r["commit_sha"]=meta["head_sha"]
                r["content_version"]="pinned_PR_head"
                r["expected_blob_sha"]=live.get("sha")
        refs.append(r)
    pd.DataFrame(refs).to_csv(target,index=False)
    pd.DataFrame(strata).to_csv(OUT / "tables/review_sampling_strata.csv",index=False)
    write_json(OUT / "review_sampling_protocol.json",{"n":len(d),"frame_n":len(f),"sampling_unit":"unique repository/PR/path within the 40-PR pilot", "strata":"tool x frozen prediction x frozen uncertainty flag", "n_per_available_stratum":8,"seed":"same fixed pilot seed with review prefix","labels":"blank; no independent human validation has occurred","blinding":"predictions and design weights are in review_sample_plan.csv; not included in the human form","inference_scope":"precision/recall, if later annotated, pertain only to this pilot-file frame and require design weights; inaccessible content may introduce further bias"},immutable=True)
    print(f"Prepared {len(d)} file candidates for content retrieval")


def make_form():
    d=pd.read_csv(OUT / "review_sample_plan.csv")
    records=[]
    for r in d.to_dict("records"):
        ref={k:r[k] for k in ["review_id","pilot_id","repo_name","pr_number","file_path","commit_sha","content_path","content_version"]}
        if isinstance(r["commit_sha"],str):
            req=content_req(r["content_repo"],r["commit_sha"],r["content_path"])
            expected=r["expected_blob_sha"] if isinstance(r["expected_blob_sha"],str) else None
            status,_=verified_content(req,expected)
            ref.update(status)
        else:ref["retrieval_status"]="no_live_path_resolution"
        for col in ["manual_is_automated_test","manual_role","manual_contains_assertions","reviewer_id","annotation_origin","annotation_timestamp","reviewer_notes","adjudicated_label"]:
            ref[col]=""
        records.append(ref)
    form=pd.DataFrame(records)
    path=OUT / "human_review.csv"
    if not path.exists(): form.to_csv(path,index=False)
    else:
        old=pd.read_csv(path,keep_default_na=False)
        assert list(old.review_id)==list(form.review_id),"Existing human form has a different sample; refusing overwrite"
        print("Preserved existing human form and all its labels")
    retrieval=form.drop(columns=[c for c in form.columns if c.startswith("manual_") or c in ["reviewer_id","annotation_origin","annotation_timestamp","reviewer_notes","adjudicated_label"]])
    retrieval.to_csv(OUT / "review_content_retrieval.csv",index=False)
    write_json(OUT / "human_annotation_status.json",{"status":"awaiting_independent_human_annotations","file_candidates":len(form),"verified_content_files":int(form.retrieval_status.eq("verified").sum()),"precision":None,"recall":None,"reason":"No trustworthy reference annotations have been supplied; assistant labels from the midpoint are not reference truth."})
    print(form.retrieval_status.value_counts().to_string())


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["plan","form"])
    args=p.parse_args()
    plan_review() if args.action=="plan" else make_form()
