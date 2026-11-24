"""Construct cached file-, link-, and unique-PR-level research tables."""
import gzip
import hashlib
import json

import numpy as np
import pandas as pd

from classifiers import SOURCE_EXTENSIONS, classify_test_file, normalize_path, testing_requirement, is_test_change
from common import DATA, FEATURES, HERE, KEY, OUT, REPO, cache, save, write_json
from matching import aggregate_features, collapse_spec_snapshots, deduplicate_prs


def text_features(specs):
    wanted = specs.set_index("file_url_sha16").file_content_sha.to_dict()
    records = []
    seen = set()
    with gzip.open(REPO / "specs.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            obj = json.loads(line)
            ident = obj["file_url_sha16"]
            if ident not in wanted:
                continue
            if ident in seen:
                raise ValueError("Duplicate text identity")
            seen.add(ident)
            text = obj.get("content")
            verified = isinstance(text, str) and hashlib.sha256(text.encode("utf-8")).hexdigest() == wanted[ident]
            flag, n = testing_requirement(text if verified else None)
            records.append({"file_url_sha16": ident, "text_hash_verified": verified, "has_testing_requirement": flag, "testing_directive_lines": n})
    return pd.DataFrame(records)


def make_review_sample(files):
    """Purposeful rule-stratified path audit; not a population accuracy sample."""
    unique = files.drop_duplicates("file_path").sort_values("file_path")
    preserved = HERE / "reviews" / "test_file_path_review.csv"
    if preserved.exists():
        # Keep the frozen 60-path audit comparable after rule improvements.
        paths = pd.read_csv(preserved, usecols=["review_id", "file_path"])
        review = paths.merge(unique, on="file_path", how="left", validate="one_to_one")
        assert review.repo_name.notna().all(), "Previously reviewed path disappeared"
        review["reference_label"] = ""
        review["review_notes"] = ""
        save(review[["review_id"] + KEY + ["file_path", "change_status", "is_code", "is_test", "test_reason", "test_uncertain", "reference_label", "review_notes"]], "test_file_review_sample", "validation")
        return
    parts = []
    for predicted in [True, False]:
        pool = unique[unique.is_test.eq(predicted)]
        # Round-robin sampling across reasons ensures both hard and ordinary cases.
        sampled = pool.groupby("test_reason", group_keys=False).sample(frac=1, random_state=520)
        sampled["rank_in_rule"] = sampled.groupby("test_reason").cumcount()
        parts.append(sampled.sort_values(["rank_in_rule", "file_path"]).head(30))
    review = pd.concat(parts).reset_index(drop=True)
    review.insert(0, "review_id", range(1, len(review) + 1))
    review["reference_label"] = ""
    review["review_notes"] = ""
    save(review[["review_id"] + KEY + ["file_path", "change_status", "is_code", "is_test", "test_reason", "test_uncertain", "reference_label", "review_notes"]], "test_file_review_sample", "validation")


def build():
    spec_cols = ["file_url_sha16", "repo_name", "file_path", "file_content_sha", "file_sha", "spec_tool", "spec_role", "file_last_commit_at", "file_first_commit_at", "commit_history_status", "repo_id", "repo_language", "repo_stars", "repo_size_kb", "repo_license_spdx_id", "content_fetched_at"]
    specs = pd.read_parquet(DATA / "spec_files.parquet", columns=spec_cols)
    features = pd.read_parquet(DATA / "spec_content_features.parquet", columns=["file_url_sha16"] + FEATURES + ["lang", "content_family"])
    assert not features.file_url_sha16.duplicated().any()
    assert set(features.file_url_sha16) == set(specs.file_url_sha16), "Feature orphans or missing spec IDs"
    specs = specs.merge(features, on="file_url_sha16", validate="one_to_one")
    specs["file_path"] = specs.file_path.map(normalize_path)
    txt = text_features(specs)
    cache(txt, "text_features")
    specs = specs.merge(txt, on="file_url_sha16", how="left", validate="one_to_one")
    snapshot = collapse_spec_snapshots(specs)
    cache(snapshot, "spec_snapshots")
    save(snapshot[snapshot.n_snapshots.gt(1)][["repo_name", "file_path", "n_snapshots", "ambiguous_snapshot"]], "duplicate_snapshot_paths", "validation")
    meta_cols = ["repo_id", "repo_language", "repo_stars", "repo_size_kb", "repo_license_spdx_id"]
    meta = specs.sort_values(["content_fetched_at", "file_url_sha16"], na_position="first").drop_duplicates("repo_name", keep="last")[["repo_name"] + meta_cols]
    save(specs.groupby("repo_name")[meta_cols].nunique(dropna=False).reset_index(), "repository_metadata_variation", "validation")
    prs = pd.read_parquet(DATA / "pull_requests.parquet")
    rawfiles = pd.read_parquet(DATA / "pr_files.parquet")
    rawfiles["file_path"] = rawfiles.file_path.map(normalize_path)
    p, files = deduplicate_prs(prs, rawfiles)
    # Each normalized file path gets one classification, shared across all PRs.
    predictions = {path: classify_test_file(path) for path in files.file_path.unique()}
    files[["is_test", "test_reason", "test_uncertain"]] = pd.DataFrame(files.file_path.map(predictions).tolist(), index=files.index)
    files["is_source_candidate"] = files.file_path.map(lambda x: "." + x.rsplit(".", 1)[-1].lower() in SOURCE_EXTENSIONS)
    files["is_source"] = files.is_source_candidate & ~files.is_test & files.is_spec.eq(0) & files.is_specdir.eq(0) & ~files.test_reason.isin(["vendored_or_generated", "fixture_sample_or_mock", "example_source_without_test_filename"])
    for status, label in [("added", "test_added"), ("modified", "test_modified"), ("removed", "test_removed"), ("renamed", "test_renamed")]:
        files[label] = is_test_change(files.is_test, files.change_status, status)
    files["test_added_strict"] = files.test_added & ~files.test_uncertain
    files["test_modified_strict"] = files.test_modified & ~files.test_uncertain
    files["source_flag_disagreement"] = files.is_source_candidate & files.is_code.eq(0)
    cache(files, "classified_files")
    save(files.groupby(["is_test", "is_code", "test_reason"], dropna=False).size().reset_index(name="n_file_observations"), "detector_is_code_audit")
    save(files.groupby(["change_status", "is_test", "test_uncertain"], dropna=False).size().reset_index(name="n_files"), "file_classification_counts")
    make_review_sample(files)
    ag = files.groupby(KEY).agg(n_observed_files=("file_path", "size"), file_record_conflict=("file_record_conflict", "max"), n_changed_source_files=("is_source", "sum"), n_dataset_code_files=("is_code", "sum"), n_visible_spec_files=("is_spec", "sum"), **{name: (name, "max") for name in ["test_added", "test_modified", "test_removed", "test_renamed", "test_added_strict", "test_modified_strict"]}).reset_index()
    p = p.merge(ag, on=KEY, how="left", validate="one_to_one")
    p["file_list_complete"] = p.n_observed_files.eq(p.n_files) & p.n_files.lt(3000) & p.files_status.eq("done") & ~p.file_record_conflict.fillna(True) & ~p.pr_metadata_conflict
    # Keep all spec paths in the audit, including unmatched, removed, and renamed.
    link = files[files.is_spec.eq(1)].merge(snapshot[["repo_name", "file_path", "file_url_sha16", "spec_tool", "spec_role", "n_snapshots", "ambiguous_snapshot", "features_complete", "file_last_commit_at", "file_first_commit_at", "commit_history_status", "has_testing_requirement", "text_hash_verified"] + FEATURES], on=["repo_name", "file_path"], how="left", validate="many_to_one")
    link["match_quality"] = np.select([link.file_url_sha16.isna(), link.ambiguous_snapshot.eq(True), ~link.features_complete.eq(True)], ["unmatched_exact_path", "ambiguous_snapshot", "missing_features"], default="exact_unambiguous")
    link = link.merge(p[KEY + ["created_at", "closed_at", "merged_at"]], on=KEY, validate="many_to_one")
    created = pd.to_datetime(link.created_at, utc=True, errors="coerce")
    end = pd.to_datetime(link.merged_at.fillna(link.closed_at), utc=True, errors="coerce")
    last = pd.to_datetime(link.file_last_commit_at, utc=True, errors="coerce")
    link["temporal_relation"] = np.select([last.isna() | created.isna() | end.isna(), last.gt(end), last.lt(created)], ["unknown_interval_or_snapshot_time", "snapshot_last_change_after_pr_end", "snapshot_last_change_before_pr_open"], default="within_pr_interval")
    link["version_verified"] = False
    link["active_spec_change"] = ~link.change_status.eq("removed")
    # Supplementary history diagnoses temporal plausibility, not blob equality.
    history = pd.read_parquet(DATA / "spec_file_commits.parquet", columns=["file_url_sha16", "commit_sha", "committed_at"])
    link["link_id"] = np.arange(len(link))
    h = link[["link_id", "file_url_sha16", "created_at", "closed_at", "merged_at"]].merge(history, on="file_url_sha16", how="left", validate="many_to_many")
    ht = pd.to_datetime(h.committed_at, utc=True, errors="coerce")
    hc = pd.to_datetime(h.created_at, utc=True, errors="coerce")
    he = pd.to_datetime(h.merged_at.fillna(h.closed_at), utc=True, errors="coerce")
    counts = h[ht.ge(hc) & ht.le(he)].groupby("link_id").commit_sha.nunique()
    link["n_known_history_commits_in_pr_interval"] = link.link_id.map(counts).fillna(0).astype(int)
    cache(link, "spec_pr_links")
    save(link.groupby(["match_quality", "temporal_relation", "change_status"]).size().reset_index(name="n_spec_file_observations"), "linkage_quality")
    linked_ids = set(link.loc[link.match_quality.eq("exact_unambiguous"), "file_url_sha16"])
    save(snapshot.loc[~snapshot.file_url_sha16.isin(linked_ids), ["repo_name", "file_path", "file_url_sha16", "ambiguous_snapshot"]], "snapshot_specs_without_exact_pr_link", "validation")
    spec_ag = pd.DataFrame([{**dict(zip(KEY, key)), **aggregate_features(group)} for key, group in link[link.active_spec_change].groupby(KEY)])
    p = p.merge(spec_ag, on=KEY, how="left", validate="one_to_one").merge(meta, on="repo_name", how="left", validate="many_to_one")
    p["has_active_spec"] = p.n_active_spec_files.fillna(0).gt(0)
    p["complete_spec_coverage"] = p.complete_spec_coverage.fillna(False).astype(bool)
    p["all_specs_temporally_overlap"] = p.all_specs_temporally_overlap.fillna(False).astype(bool)
    reasons = []
    for row in p.itertuples():
        why = []
        if not row.file_list_complete: why.append("incomplete_or_conflicting_file_list")
        if not row.has_active_spec: why.append("no_active_visible_spec")
        elif not row.complete_spec_coverage: why.append("unmatched_ambiguous_or_missing_active_spec_features")
        if not row.n_changed_source_files > 0: why.append("no_non_test_source_changes")
        reasons.append(";".join(why))
    p["exclusion_reasons"] = reasons
    p["in_primary_snapshot_analysis"] = p.exclusion_reasons.eq("")
    p["in_temporal_sensitivity"] = p.in_primary_snapshot_analysis & p.all_specs_temporally_overlap
    p["version_verified"] = False
    for outcome in ["test_added", "test_modified", "test_removed", "test_renamed", "test_added_strict", "test_modified_strict"]:
        p[outcome] = p[outcome].astype("Int64")
    assert not p.duplicated(KEY).any()
    cache(p, "all_pr_observations")
    save(p, "all_pr_observations")
    primary = p[p.in_primary_snapshot_analysis].copy()
    primary.to_parquet(OUT / "analysis_dataset.parquet", index=False)
    primary.to_csv(OUT / "analysis_dataset.csv", index=False)
    save(p.loc[~p.in_primary_snapshot_analysis, KEY + ["tools", "exclusion_reasons", "n_visible_spec_files", "n_active_spec_files", "n_exact_matched_specs"]], "excluded_prs", "validation")
    # Independent reasons can overlap; report both exact combinations and waterfall.
    save(p.groupby("exclusion_reasons", dropna=False).size().reset_index(name="n_prs"), "exclusion_reason_combinations")
    stages = [("unique_prs", np.ones(len(p), dtype=bool)), ("complete_file_lists", p.file_list_complete), ("active_spec", p.has_active_spec), ("complete_exact_spec_features", p.complete_spec_coverage), ("non_test_source_change", p.n_changed_source_files.gt(0))]
    keep = np.ones(len(p), dtype=bool)
    flow = []
    for name, criterion in stages:
        keep &= criterion
        flow.append({"stage": name, "n_prs": int(keep.sum()), "n_repos": int(p.loc[keep, "repo_name"].nunique())})
    save(pd.DataFrame(flow), "sample_flow")
    summary = {"raw_pr_records": len(prs), "unique_prs": len(p), "deduplicated_file_observations": len(files), "snapshot_paths": len(snapshot), "ambiguous_snapshot_paths": int(snapshot.ambiguous_snapshot.sum()), "prs_with_any_unambiguous_path_match": int(link[link.match_quality.eq("exact_unambiguous")].drop_duplicates(KEY).shape[0]), "primary_snapshot_prs": len(primary), "primary_repositories": primary.repo_name.nunique(), "temporal_overlap_prs": int(p.in_temporal_sensitivity.sum()), "verified_pr_time_versions": 0, "predicted_test_files_is_code_zero": int((files.is_test & files.is_code.eq(0)).sum()), "text_hash_verified": int(txt.text_hash_verified.sum()), "text_records": len(txt)}
    write_json(OUT / "tables" / "build_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    build()
