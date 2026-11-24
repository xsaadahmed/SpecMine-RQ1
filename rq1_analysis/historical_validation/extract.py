"""Verify downloaded blobs, extract matched features, and build separate cohorts."""
import base64
import gzip
import hashlib
import json
import math

import pandas as pd

from features import RULE_VERSION, structural_features
from hv_common import BASELINE, CACHE, FEATURES, FROZEN, KEY, OUT, REPO, api_req, cached, content_req, data_for, pr_req, protect_baseline, write_json
from plan import active_links, anchor, full_list, pilot, resolved_specs


def git_blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def verified_content(req, expected_blob=None):
    record = cached(req)
    if record is None: return {"retrieval_status": "not_attempted"}, None
    if not record.get("ok"):
        return {"retrieval_status": "remote_error", "retrieval_error": record.get("detail",record.get("error"))}, None
    d = record["data"]
    try:
        if d["encoding"] == "base64":
            content = base64.b64decode("".join(d["content"].split()),validate=True)
        elif d["encoding"] == "utf-8": content = d["content"].encode("utf-8")
        else: raise ValueError("Unsupported or absent content encoding")
        blob = git_blob_sha(content)
        if blob != d["sha"]: raise ValueError("Response blob SHA does not match bytes")
        if expected_blob and expected_blob != blob: raise ValueError("PR changed-file blob does not match pinned content")
        text = content.decode("utf-8-sig")
    except (ValueError, UnicodeError, KeyError, TypeError) as e:
        return {"retrieval_status": "verification_failed", "retrieval_error": str(e)}, None
    sha256 = hashlib.sha256(content).hexdigest()
    path = OUT / "content" / (sha256+".txt")
    if path.exists(): assert path.read_bytes() == content
    else: path.write_bytes(content)
    return {"retrieval_status": "verified", "blob_sha": blob, "content_sha256": sha256, "n_content_bytes": len(content), "content_reference": path.relative_to(OUT.parent).as_posix(), "pinned_url": d.get("display_url"), "retrieved_at": record["retrieved_at"], "request_id": req["id"]}, text


def snapshots_for(ids):
    result = {}
    wanted = set(ids)
    spine = pd.read_parquet(REPO / "data/spec_files.parquet", columns=["file_url_sha16","file_content_sha"])
    expected = spine.set_index("file_url_sha16").file_content_sha.to_dict()
    with gzip.open(REPO / "specs.jsonl.gz","rt",encoding="utf-8") as stream:
        for line in stream:
            obj=json.loads(line)
            ident=obj["file_url_sha16"]
            if ident not in wanted: continue
            text=obj.get("content")
            if not isinstance(text,str) or hashlib.sha256(text.encode("utf-8")).hexdigest()!=expected[ident]:
                raise ValueError("Frozen snapshot text hash mismatch")
            result[ident]={"snapshot_content_sha256":expected[ident], **structural_features(text)}
    assert set(result)==wanted
    return result


def safe_number(x):
    return None if x is None or (isinstance(x,float) and math.isnan(x)) else x


def extract():
    protect_baseline()
    p=pilot()
    links=resolved_specs()
    texts=snapshots_for(r["file_url_sha16"] for r in links)
    rows=[]
    earlier=[]
    for r in links:
        repo,num=r["repo_name"],r["pr_number"]
        meta=data_for(pr_req(repo,num))
        base={"pilot_id":r["pilot_id"],"repo_name":repo,"pr_number":num,"baseline_path":r["file_path"],"resolved_path":r["resolved_path"],"resolution_status":r["resolution_status"],"baseline_change_status":r["change_status"],"live_status":r.get("live_status"),"previous_filename":r.get("previous_filename"),"snapshot_id":r["file_url_sha16"],"head_sha":meta["head_sha"] if meta else None}
        snap=texts[r["file_url_sha16"]]
        base["snapshot_content_sha256"]=snap["snapshot_content_sha256"]
        base["same_rule_snapshot_n_words"]=snap["n_words"]
        for name in FEATURES:
            base["supplied_snapshot_"+name]=r[name]
            base["same_rule_snapshot_"+name]=snap[name]
        if r["resolution_status"] in ["exact_live_path","api_previous_filename"]:
            req=content_req(repo,meta["head_sha"],r["resolved_path"])
            status,text=verified_content(req,r["head_blob_sha_expected"])
            base.update(status)
            if text is not None:
                parsed=structural_features(text)
                base.update({"head_"+k:v for k,v in parsed.items()})
                base["content_identical_to_snapshot"]=status["content_sha256"]==snap["snapshot_content_sha256"]
                for name in FEATURES:
                    base["version_label_mismatch_"+name]=parsed[name]!=snap[name]
                    base["definition_label_mismatch_"+name]=snap[name]!=r[name]
        else: base["retrieval_status"]="unresolved_path_no_snapshot_fallback"
        rows.append(base)
        a=anchor(repo,num)
        pre={k:base[k] for k in ["pilot_id","repo_name","pr_number","baseline_path","resolved_path"]}
        pre.update(anchor_status=a["status"],genuine_preimplementation_proven=False)
        if a["status"]=="anchor_established" and r["resolved_path"]:
            path=r.get("previous_filename") or r["resolved_path"]
            pre.update(anchor_sha=a["anchor_sha"],first_implementation_sha=a["first_implementation_sha"],earlier_path=path,earlier_commits_without_detected_executable_changes=a["earlier_commits_without_detected_executable_changes"])
            req=content_req(repo,a["anchor_sha"],path)
            status,text=verified_content(req)
            pre.update(status)
            if text is not None:
                pre.update(structural_features(text))
                pre["present_before_first_observed_implementation"]=True
            else: pre["present_before_first_observed_implementation"]=False
        else: pre["retrieval_status"]="no_validated_earlier_anchor"
        earlier.append(pre)
    sf=pd.DataFrame(rows)
    ef=pd.DataFrame(earlier)
    sf.to_csv(OUT / "historical_spec_files.csv",index=False)
    ef.to_csv(OUT / "earlier_spec_files.csv",index=False)
    # Reconstruct file-set validity independently of successful content retrieval.
    baseline_files=pd.read_parquet(BASELINE / "outputs/intermediate/classified_files.parquet")
    aggregate=[]
    anchor_records=[]
    for r in p.to_dict("records"):
        repo,num=r["repo_name"],r["pr_number"]
        meta=data_for(pr_req(repo,num))
        files=full_list(repo,num,"files")
        a=anchor(repo,num)
        anchor_records.append({"pilot_id":r["pilot_id"],"repo_name":repo,"pr_number":num,**{k:v for k,v in a.items() if k!="request"}})
        selected=sf[sf.pilot_id.eq(r["pilot_id"])]
        pre=ef[ef.pilot_id.eq(r["pilot_id"])]
        original=baseline_files[baseline_files.repo_name.eq(repo)&baseline_files.pr_number.eq(num)]
        expected={(x.file_path,x.change_status) for x in original.itertuples()}
        live_set={(x["filename"],x["status"]) for x in files} if files is not None else None
        r["live_diff_matches_frozen_baseline"] = live_set==expected
        r["metadata_available"] = meta is not None
        r["live_files_complete"] = files is not None
        r["n_expected_active_specs"] = len(selected)
        r["n_verified_head_specs"] = int(selected.retrieval_status.eq("verified").sum())
        r["head_content_complete"] = bool(len(selected) and selected.retrieval_status.eq("verified").all())
        r["in_historical_head_cohort"] = r["head_content_complete"] and r["live_diff_matches_frozen_baseline"]
        r["head_sha"] = meta["head_sha"] if meta else None
        r["head_version_verified"] = r["head_content_complete"]
        r["genuine_preimplementation_proven"] = False
        r["earlier_anchor_status"] = a["status"]
        r["earlier_anchor_sha"] = a.get("anchor_sha")
        r["n_verified_earlier_specs"] = int(pre.retrieval_status.eq("verified").sum())
        r["in_earlier_complete_cohort"] = r["in_historical_head_cohort"] and len(pre)>0 and pre.retrieval_status.eq("verified").all()
        for name in FEATURES:
            r["supplied_snapshot_"+name] = r[name]
            r["same_rule_snapshot_"+name] = int(selected["same_rule_snapshot_"+name].max())
            r["historical_head_"+name] = int(selected["head_"+name].max()) if r["head_content_complete"] else None
            r["earlier_"+name] = int(pre[name].max()) if r["in_earlier_complete_cohort"] else None
        r["historical_head_n_words"] = selected.head_n_words.sum() if r["head_content_complete"] else None
        r["snapshot_n_words"] = r.pop("n_words")
        for name in FEATURES: r.pop(name, None)
        for name in ["version_verified", "in_primary_snapshot_analysis", "exclusion_reasons", "in_temporal_sensitivity"]:
            if name in r: r["baseline_"+name] = r.pop(name)
        if files is not None:
            for status,name in [("added","test_added"),("modified","test_modified")]:
                r["live_"+name]=int(any(FROZEN.classify_test_file(f["filename"])[0] and f["status"]==status for f in files))
                if r["live_diff_matches_frozen_baseline"]: assert r["live_"+name]==r[name]
        reasons=[]
        if not r["metadata_available"]:reasons.append("metadata_inaccessible")
        if not r["live_diff_matches_frozen_baseline"]:reasons.append("live_net_diff_different_or_unavailable")
        if not r["head_content_complete"]:reasons.append("historical_head_spec_content_incomplete")
        r["historical_exclusion_reasons"]=";".join(reasons)
        aggregate.append(r)
    cohort=pd.DataFrame(aggregate)
    cohort.to_csv(OUT / "pilot_observations.csv",index=False)
    cohort[cohort.in_historical_head_cohort].to_csv(OUT / "historical_head_analysis_cohort.csv",index=False)
    cohort[cohort.in_earlier_complete_cohort].to_csv(OUT / "earlier_complete_analysis_cohort.csv",index=False)
    write_json(OUT / "anchor_audit.json",anchor_records)
    summary={"planned_prs":len(p),"planned_repositories":p.repo_name.nunique(),"planned_active_spec_observations":len(sf),"verified_head_spec_observations":int(sf.retrieval_status.eq("verified").sum()),"complete_head_prs":int(cohort.head_content_complete.sum()),"historical_head_analysis_prs":int(cohort.in_historical_head_cohort.sum()),"verified_earlier_spec_observations":int(ef.retrieval_status.eq("verified").sum()),"complete_earlier_prs":int(cohort.in_earlier_complete_cohort.sum()),"anchors_established":int(cohort.earlier_anchor_status.eq("anchor_established").sum()),"genuine_preimplementation_prs":0,"feature_rule_version":RULE_VERSION}
    write_json(OUT / "historical_build_summary.json",summary)
    print(json.dumps(summary,indent=2))


if __name__ == "__main__": extract()
