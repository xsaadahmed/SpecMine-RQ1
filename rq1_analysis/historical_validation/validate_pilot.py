"""Checks actual cached evidence, cohort completeness, and baseline immutability."""
import hashlib
import json
import zipfile

import pandas as pd

from extract import git_blob_sha
from hv_common import BASELINE, CACHE, FEATURES, HERE, KEY, OUT, REPO, data_for, digest, pr_req, protect_baseline, write_json
from plan import anchor, pilot


def preserve_archive():
    manifest=json.loads((HERE / "baseline_manifest.json").read_text(encoding="utf-8"))
    entries={name:entry for name,entry in manifest.items() if name.startswith("rq1_analysis/")}
    path=HERE / "midpoint_baseline_nov05.zip"
    if not path.exists():
        with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name in entries:archive.write(REPO / name,name)
    with zipfile.ZipFile(path) as archive:
        assert set(archive.namelist())==set(entries)
        for name,entry in entries.items():assert hashlib.sha256(archive.read(name)).hexdigest()==entry["sha256"]
    return {"archive":path.name,"sha256":digest(path),"files":len(entries),"raw_dataset_copied":False}


def validate():
    baseline_n=protect_baseline()
    archive=preserve_archive()
    p=pilot();d=pd.read_csv(OUT / "pilot_observations.csv");f=pd.read_csv(OUT / "historical_spec_files.csv");e=pd.read_csv(OUT / "earlier_spec_files.csv")
    assert len(p)==40 and len(d)==40 and not d.duplicated(KEY).any()
    assert p.groupby("tool").size().eq(20).all()
    assert p.groupby("tool").has_acceptance_criteria.sum().eq(8).all()
    strata=pd.read_csv(OUT / "tables/pilot_sampling_strata.csv")
    assert (strata.sample_n/strata.frame_n).eq(strata.inclusion_probability).all() or ((strata.sample_n/strata.frame_n-strata.inclusion_probability).abs()<1e-12).all()
    head=d[d.in_historical_head_cohort]
    for r in head.itertuples():
        subset=f[f.pilot_id.eq(r.pilot_id)]
        assert len(subset)==r.n_expected_active_specs and subset.retrieval_status.eq("verified").all()
        assert r.live_diff_matches_frozen_baseline
        for feature in FEATURES:
            assert getattr(r,"historical_head_"+feature)==subset["head_"+feature].max()
    assert d.loc[~d.head_content_complete,["historical_head_"+x for x in FEATURES]].isna().all().all(),"Missing historical text silently became snapshot or zero"
    for r in f[f.retrieval_status.eq("verified")].itertuples():
        path=HERE / r.content_reference
        raw=path.read_bytes()
        assert git_blob_sha(raw)==r.blob_sha
        assert hashlib.sha256(raw).hexdigest()==r.content_sha256
        assert r.head_sha in r.pinned_url
    for r in d[d.in_earlier_complete_cohort].itertuples():
        a=anchor(r.repo_name,r.pr_number)
        assert a["status"]=="anchor_established" and a["anchor_sha"]==r.earlier_anchor_sha
        subset=e[e.pilot_id.eq(r.pilot_id)]
        assert len(subset)==r.n_expected_active_specs and subset.retrieval_status.eq("verified").all()
    assert not d.genuine_preimplementation_proven.any()
    reviews=pd.read_csv(OUT / "human_review.csv")
    assert reviews.manual_is_automated_test.isna().all() and reviews.adjudicated_label.isna().all(),"The delivered template must remain blank"
    assert not any(c in reviews for c in ["is_test","test_reason","reference_label"]),"Human form leaked detector/assistant labels"
    assert len(reviews)>=50 and not reviews.review_id.duplicated().any()
    for r in reviews[reviews.retrieval_status.eq("verified")].itertuples():
        assert r.commit_sha in r.pinned_url and hashlib.sha256((HERE/r.content_reference).read_bytes()).hexdigest()==r.content_sha256
    records=[json.loads(p.read_text(encoding="utf-8")) for p in CACHE.glob("*.json")]
    errors=[r for r in records if not r["ok"]]
    cache_manifest={path.name:{"sha256":digest(path),"bytes":path.stat().st_size} for path in sorted(CACHE.glob("*.json"))}
    write_json(OUT / "acquisition_cache_manifest.json",cache_manifest,immutable=True)
    status={"status":"passed","baseline_files_unchanged":baseline_n,"archive":archive,"selected_prs":len(d),"historical_head_cohort":len(head),"earlier_complete_cohort":int(d.in_earlier_complete_cohort.sum()),"human_form_candidates":len(reviews),"human_form_verified_contents":int(reviews.retrieval_status.eq("verified").sum()),"human_labels_supplied":0,"cache_records":len(records),"failed_content_requests":len(errors),"error_scope":"All cached errors are reported, never substituted with snapshots","checks":["frozen baseline SHA-256 and archive bytes","40 PR identities and predeclared strata","full active spec coverage and blob equality","unknown historical predictors remain missing","earlier anchors require verified linear history prefix","human form remains blank and blinded","all pinned review references hashed"]}
    write_json(OUT / "validation_results.json",status)
    print(json.dumps(status,indent=2))


if __name__=="__main__":validate()
