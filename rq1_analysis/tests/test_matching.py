import pandas as pd

from matching import aggregate_features, collapse_spec_snapshots, deduplicate_prs


def spec(ident, path="specs/a/spec.md", content="abc", acceptance=0):
    return dict(file_url_sha16=ident, repo_name="org/repo", file_path=path,
                file_content_sha=content, has_acceptance_criteria=acceptance,
                has_edge_cases=1, has_requirements=1, n_words=100,
                file_last_commit_at="2026-01-01", file_first_commit_at="2025-12-01")


def test_identical_snapshots_collapse_without_multiplication():
    out = collapse_spec_snapshots(pd.DataFrame([spec("a"), spec("b")]))
    assert len(out) == 1
    assert out.iloc[0].n_snapshots == 2
    assert not out.iloc[0].ambiguous_snapshot


def test_different_content_never_arbitrarily_selects_a_version():
    out = collapse_spec_snapshots(pd.DataFrame([spec("a"), spec("b", content="xyz")]))
    assert out.iloc[0].ambiguous_snapshot


def test_feature_disagreement_is_also_ambiguous():
    out = collapse_spec_snapshots(pd.DataFrame([spec("a"), spec("b", acceptance=1)]))
    assert out.iloc[0].ambiguous_snapshot


def test_archive_and_current_paths_are_distinct():
    out = collapse_spec_snapshots(pd.DataFrame([spec("a"), spec("b", path="specs/archive/a/spec.md")]))
    assert len(out) == 2


def test_multiple_tools_do_not_duplicate_prs_or_files():
    prs = pd.DataFrame([dict(tool=t, repo_name="org/repo", pr_number=1, id=i, n_files=1) for i,t in enumerate(["a", "b"])])
    files = pd.DataFrame([dict(tool=t, repo_name="org/repo", pr_number=1, id=i, file_path="tests/test_a.py", change_status="added", additions=1, deletions=0, is_spec=0, is_specdir=0, is_code=1) for i,t in enumerate(["a", "b"])])
    p, f = deduplicate_prs(prs, files)
    assert len(p) == len(f) == 1
    assert p.iloc[0].tools == "a|b"
    assert p.iloc[0].tool == "multiple"
    files.loc[1, "change_status"] = "removed"
    assert deduplicate_prs(prs, files)[1].iloc[0].file_record_conflict


def test_incomplete_coverage_does_not_mean_absence():
    g = pd.DataFrame([dict(match_quality="exact_unambiguous", temporal_relation="within_pr_interval", has_acceptance_criteria=1, has_edge_cases=0, has_requirements=1, n_words=100, has_testing_requirement=0), dict(match_quality="unmatched_exact_path", temporal_relation="unknown", has_acceptance_criteria=None, has_edge_cases=None, has_requirements=None, n_words=None, has_testing_requirement=None)])
    out = aggregate_features(g)
    assert not out["complete_spec_coverage"]
    assert pd.isna(out["has_acceptance_criteria"])
    out = aggregate_features(g.iloc[:1])
    assert out["has_acceptance_criteria"] == 1
    assert out["n_words"] == 100
