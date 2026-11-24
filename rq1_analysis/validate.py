"""Cross-check derived results and consume the explicit, preserved manual audits."""
import json

import numpy as np
import pandas as pd

from common import FEATURES, HERE, KEY, OUT, save, write_json
from inspect_data import input_manifest


def validate():
    expected = json.loads((OUT / "inspection" / "input_manifest.json").read_text())
    assert input_manifest() == expected, "Original input changed"
    p = pd.read_parquet(OUT / "intermediate" / "all_pr_observations.parquet")
    d = pd.read_parquet(OUT / "analysis_dataset.parquet")
    f = pd.read_parquet(OUT / "intermediate" / "classified_files.parquet")
    l = pd.read_parquet(OUT / "intermediate" / "spec_pr_links.parquet")
    checks = ["all original inputs match SHA-256 baseline"]
    assert not d.duplicated(KEY).any() and not p.duplicated(KEY).any()
    assert not f.duplicated(KEY + ["file_path"]).any()
    checks.append("unique PR identity and unique PR/file paths after tool union")
    assert d.in_primary_snapshot_analysis.all() and d.file_list_complete.all()
    assert d.complete_spec_coverage.all() and d.n_changed_source_files.gt(0).all()
    assert d[FEATURES].notna().all().all()
    active = l[l.active_spec_change].merge(d[KEY], on=KEY, validate="many_to_one")
    assert active.match_quality.eq("exact_unambiguous").all()
    assert not active.version_verified.any() and not d.version_verified.any()
    checks.append("every primary PR has complete, unambiguous active spec coverage and source changes")
    for status, outcome in [("added", "test_added"), ("modified", "test_modified"), ("removed", "test_removed"), ("renamed", "test_renamed")]:
        expected_outcome = f.assign(expected=f.is_test & f.change_status.eq(status)).groupby(KEY).expected.max().reset_index()
        compare = p.merge(expected_outcome, on=KEY, validate="one_to_one")
        assert compare[outcome].astype(bool).eq(compare.expected).all()
    checks.append("all four change-status outcomes independently reconstruct from unique files")
    grouped = active.groupby(KEY)
    for col in FEATURES:
        agg = grouped[col].sum() if col == "n_words" else grouped[col].max()
        actual = d.set_index(KEY)[col].reindex(agg.index)
        assert np.allclose(actual, agg)
    checks.append("PR feature aggregation agrees with underlying matched spec files")
    review = pd.read_csv(HERE / "reviews" / "test_file_path_review.csv")
    sampled = pd.read_csv(OUT / "validation" / "test_file_review_sample.csv")
    assert len(review) >= 50 and not review.file_path.duplicated().any()
    assert review.reference_label.isin(["test", "non_test", "uncertain"]).all()
    assert set(review.file_path) == set(sampled.file_path), "Audit no longer matches current detector sample"
    current = f.drop_duplicates("file_path").set_index("file_path").is_test
    assert review.is_test.eq(review.file_path.map(current)).all(), "Detector changed after path review"
    determinate = review.reference_label.ne("uncertain")
    agreement = review.loc[determinate, "is_test"].eq(review.loc[determinate, "reference_label"].eq("test"))
    review["current_test_reason"] = review.file_path.map(f.drop_duplicates("file_path").set_index("file_path").test_reason)
    review["current_test_uncertain"] = review.file_path.map(f.drop_duplicates("file_path").set_index("file_path").test_uncertain)
    save(review, "reviewed_test_file_examples", "validation")
    save(review[review.reference_label.eq("uncertain")], "uncertain_review_examples", "validation")
    audit = {"reviewed_paths": len(review), "predicted_tests": int(review.is_test.sum()), "predicted_non_tests": int((~review.is_test).sum()), "determinate_path_labels": int(determinate.sum()), "uncertain": int((~determinate).sum()), "path_label_agreements": int(agreement.sum()), "path_label_disagreements": int((~agreement).sum()), "limitation": "Unblinded assistant path review of a purposeful rule-stratified sample; no file contents or execution were checked. This is not independent human ground truth or a population precision/recall estimate."}
    targeted = pd.read_csv(HERE / "reviews" / "targeted_negative_path_review.csv")
    targeted["current_prediction"] = targeted.file_path.map(current)
    assert targeted.current_prediction.notna().all()
    known = targeted.reference_label.ne("uncertain")
    assert targeted.loc[known, "current_prediction"].eq(targeted.loc[known, "reference_label"].eq("test")).all(), "Unresolved determinate targeted audit disagreement"
    save(targeted, "targeted_negative_path_review", "validation")
    audit["targeted_negative_review"] = {"paths_reviewed": len(targeted), "path_labeled_missed_tests_before_rule_correction": int(targeted.reference_label.eq("test").sum()), "uncertain": int(targeted.reference_label.eq("uncertain").sum()), "determinate_disagreements_after_correction": 0}
    audit["total_unique_reviewed_paths"] = len(set(review.file_path) | set(targeted.file_path))
    audit["total_unique_uncertain_paths"] = len(set(review.loc[review.reference_label.eq("uncertain"), "file_path"]) | set(targeted.loc[targeted.reference_label.eq("uncertain"), "file_path"]))
    write_json(OUT / "validation" / "file_review_summary.json", audit)
    matches = pd.read_csv(HERE / "reviews" / "spec_pr_match_review.csv")
    tested = matches.merge(l, on=KEY + ["file_path", "file_url_sha16"], how="left", validate="one_to_one", suffixes=("_review", "_current"), indicator=True)
    assert tested._merge.eq("both").all()
    assert tested.match_quality_current.eq("exact_unambiguous").all()
    assert tested.tools_review.eq(tested.tools_current).all()
    assert tested.spec_tool_review.eq(tested.spec_tool_current).all()
    save(matches, "reviewed_spec_pr_matches", "validation")
    checks.append(f"{audit['total_unique_reviewed_paths']} manually reviewed file paths and {len(matches)} inspected local spec/PR links preserved")
    # Examine template signatures and temporal plausibility without claiming versions.
    save(active.groupby(["temporal_relation", "commit_history_status"]).agg(n_spec_files=("file_path", "size"), with_known_commit_in_interval=("n_known_history_commits_in_pr_interval", lambda x: int(x.gt(0).sum()))).reset_index(), "primary_snapshot_temporal_audit", "validation")
    timing = active.assign(after_end=active.temporal_relation.eq("snapshot_last_change_after_pr_end"), before_open=active.temporal_relation.eq("snapshot_last_change_before_pr_open")).groupby(KEY).agg(any_snapshot_changed_after_end=("after_end", "max"), any_snapshot_last_change_before_open=("before_open", "max"))
    timing_summary = {"primary_prs": len(d), "prs_with_any_snapshot_change_after_pr_end": int(timing.any_snapshot_changed_after_end.sum()), "prs_with_any_snapshot_last_change_before_pr_open": int(timing.any_snapshot_last_change_before_open.sum()), "all_snapshots_last_changed_within_pr_interval": int(d.in_temporal_sensitivity.sum()), "pr_time_version_verified": 0}
    write_json(OUT / "validation" / "temporal_summary.json", timing_summary)
    write_json(OUT / "validation" / "validation_results.json", {"status": "passed", "checks": checks, "manual_file_audit": audit, "temporal_audit": timing_summary})
    print("Validation passed:")
    for c in checks: print("  " + c)


if __name__ == "__main__":
    validate()
