"""Pure matching helpers tested separately from the sample pipeline."""
import pandas as pd

from common import FEATURES, KEY


def collapse_spec_snapshots(specs):
    """Keep one row per exact repo/path only when content AND features agree.

    No case folding, historical-path inference, or selection by PR outcome.
    Choose a stable representative only after marking conflicts. Max last-commit
    time is conservative for the timing diagnostic over identical-content copies.
    """
    pathkey = ["repo_name", "file_path"]
    assert not specs.file_url_sha16.duplicated().any(), "Nonunique feature identity"
    g = specs.groupby(pathkey, dropna=False, sort=False)
    counts = g.size().rename("n_snapshots")
    varying = g[["file_content_sha"] + FEATURES].nunique(dropna=False)
    ambiguous = varying.gt(1).any(axis=1).rename("ambiguous_snapshot")
    rep = specs.sort_values("file_url_sha16").drop_duplicates(pathkey).set_index(pathkey)
    rep = rep.join(counts).join(ambiguous)
    for col in ["file_last_commit_at", "file_first_commit_at"]:
        if col in specs:
            times = pd.to_datetime(specs[col], utc=True, errors="coerce")
            tmp = specs[pathkey].assign(time=times).groupby(pathkey).time
            rep[col] = tmp.max() if "last" in col else tmp.min()
    rep["features_complete"] = rep[FEATURES].notna().all(axis=1) & rep.file_content_sha.notna()
    return rep.reset_index()


def deduplicate_prs(prs, files):
    """Union tool discoveries without treating them as independent observations."""
    assert not prs.duplicated(["tool"] + KEY).any(), "Duplicate PR/tool keys"
    assert not files.duplicated(["tool"] + KEY + ["file_path"]).any(), "Duplicate file/tool keys"
    assert files.merge(prs[["tool"] + KEY], on=["tool"] + KEY, how="left", indicator=True)._merge.eq("both").all(), "Orphan file rows"
    stable = [c for c in ["created_at", "closed_at", "merged_at", "state", "is_merged", "n_files", "additions", "deletions"] if c in prs]
    pg = prs.groupby(KEY, sort=False)
    out = prs.sort_values("tool").drop_duplicates(KEY).drop(columns=["id", "tool", "author_login", "title", "head_branch", "base_branch"], errors="ignore").set_index(KEY)
    out["tools"] = pg.tool.agg(lambda x: "|".join(sorted(set(x))))
    out["tool"] = out.tools.where(~out.tools.str.contains("|", regex=False), "multiple")
    out["n_tool_records"] = pg.size()
    out["pr_metadata_conflict"] = pg[stable].nunique(dropna=False).gt(1).any(axis=1)
    fk = KEY + ["file_path"]
    fg = files.groupby(fk, sort=False)
    f = files.sort_values("tool").drop_duplicates(fk).drop(columns=["id", "tool"]).set_index(fk)
    f["tools"] = fg.tool.agg(lambda x: "|".join(sorted(set(x))))
    f["file_record_conflict"] = fg[["change_status", "additions", "deletions"]].nunique(dropna=False).gt(1).any(axis=1)
    # Tool-specific spec/code flags can legitimately differ; union flags, not rows.
    for col in ["is_spec", "is_specdir", "is_code"]:
        f[col] = fg[col].max()
    return out.reset_index(), f.reset_index()


def aggregate_features(group):
    """Any-spec presence, total words; absence requires complete coverage."""
    result = {}
    complete = group.match_quality.eq("exact_unambiguous").all()
    result["complete_spec_coverage"] = bool(complete)
    for col in FEATURES + ["has_testing_requirement"]:
        values = group[col]
        if col == "n_words":
            result[col] = values.sum(min_count=len(group)) if complete else float("nan")
        else:
            result[col] = values.max() if complete and values.notna().all() else float("nan")
    result["all_specs_temporally_overlap"] = bool(complete and group.temporal_relation.eq("within_pr_interval").all())
    result["n_active_spec_files"] = len(group)
    result["n_exact_matched_specs"] = int(group.match_quality.eq("exact_unambiguous").sum())
    return result
