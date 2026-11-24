"""Freeze a probability sample before inspecting remote content or availability."""
import json

import pandas as pd

from hv_common import BASELINE, HERE, KEY, OUT, SEED, hash_order, protect_baseline, write_json


def select_pilot():
    protect_baseline()
    d = pd.read_parquet(BASELINE / "outputs" / "analysis_dataset.parquet")
    frame = d[d.tool.isin(["openspec", "speckit"]) & d.closed_at.notna()].copy()
    strata = ["tool", "has_acceptance_criteria", "has_edge_cases", "test_added"]
    for c in strata[1:]: frame[c] = frame[c].astype(int)
    counts = frame.groupby(strata).size().rename("frame_n").reset_index()
    counts["sample_n"] = 0
    for tool in ["openspec", "speckit"]:
        for ac, target in [(0, 12), (1, 8)]:
            ix = counts.index[counts.tool.eq(tool) & counts.has_acceptance_criteria.eq(ac)].tolist()
            while counts.loc[ix, "sample_n"].sum() < target:
                progress = False
                for index in ix:
                    if counts.loc[ix, "sample_n"].sum() >= target: break
                    if counts.loc[index, "sample_n"] < counts.loc[index, "frame_n"]:
                        counts.loc[index, "sample_n"] += 1
                        progress = True
                if not progress: raise ValueError("Insufficient stratum capacity")
    selected = []
    for row in counts.itertuples():
        mask = frame.tool.eq(row.tool) & frame.has_acceptance_criteria.eq(row.has_acceptance_criteria) & frame.has_edge_cases.eq(row.has_edge_cases) & frame.test_added.eq(row.test_added)
        pool = frame[mask].copy()
        pool["selection_hash"] = [hash_order(f"{r}/{n}") for r,n in zip(pool.repo_name, pool.pr_number)]
        pool = pool.sort_values("selection_hash").head(row.sample_n)
        pool["stratum_frame_n"] = row.frame_n
        pool["stratum_sample_n"] = row.sample_n
        pool["inclusion_probability"] = row.sample_n / row.frame_n
        pool["design_weight"] = row.frame_n / row.sample_n
        selected.append(pool)
    pilot = pd.concat(selected, ignore_index=True).sort_values(strata + ["selection_hash"]).reset_index(drop=True)
    pilot.insert(0, "pilot_id", [f"P{i:02d}" for i in range(1, len(pilot)+1)])
    assert len(pilot) == 40 and not pilot.duplicated(KEY).any()
    path = OUT / "pilot_sample.csv"
    if path.exists():
        old = pd.read_csv(path)
        assert old[KEY].equals(pilot[KEY]), "Frozen sample would change; create a new run instead"
    else:
        pilot.to_csv(path, index=False)
        counts["inclusion_probability"] = counts.sample_n / counts.frame_n
        counts.to_csv(OUT / "tables" / "pilot_sampling_strata.csv", index=False)
        write_json(OUT / "sampling_protocol.json", {"seed": SEED, "pilot_n": 40, "frame_n": len(frame), "baseline_n": len(d), "tools": ["openspec", "speckit"], "closed_prs_only": True, "per_tool": {"acceptance_positive": 8, "acceptance_negative": 12}, "selection": "Hash-ordered simple random sample within tool x acceptance x edge x baseline test-added strata; round-robin quota allocation", "no_availability_substitution": True, "pilot_repositories": int(pilot.repo_name.nunique()), "frame_sha_protected_by_baseline_manifest": True}, immutable=True)
    print(counts.to_string(index=False))
    print(f"Pilot: {len(pilot)} PRs / {pilot.repo_name.nunique()} repositories; frame: {len(frame)}")
    return pilot


if __name__ == "__main__": select_pilot()
