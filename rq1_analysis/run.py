"""Reproducible stage runner with input fingerprints and content-based caching."""
import argparse
import hashlib
import json
import subprocess
import sys

from common import HERE, OUT, sha256, write_json
from inspect_data import inspect

BUILD_TABLES = ["detector_is_code_audit", "file_classification_counts", "linkage_quality", "all_pr_observations", "exclusion_reason_combinations", "sample_flow"]
BUILD_VALIDATION = ["duplicate_snapshot_paths", "repository_metadata_variation", "test_file_review_sample", "snapshot_specs_without_exact_pr_link", "excluded_prs"]


def stage_outputs(stage):
    if stage == "build":
        return sorted(OUT.glob("analysis_dataset.*")) + sorted((OUT / "intermediate").glob("*.parquet")) + [OUT / "tables" / f"{x}.csv" for x in BUILD_TABLES] + [OUT / "tables" / "build_summary.json"] + [OUT / "validation" / f"{x}.csv" for x in BUILD_VALIDATION]
    return sorted(p for p in (OUT / "tables").iterdir() if p.stem not in BUILD_TABLES + ["build_summary"]) + sorted((OUT / "figures").iterdir())


def signature(names):
    h = hashlib.sha256()
    for path in names:
        h.update(str(path).encode())
        h.update(sha256(path).encode())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["all", "inspect", "build", "analyze", "validate", "report"], default="all")
    parser.add_argument("--force", action="store_true", help="Rebuild cached data and statistical outputs")
    args = parser.parse_args()
    statepath = OUT / "stage_cache.json"
    state = json.loads(statepath.read_text()) if statepath.exists() else {}
    # Always verify original bytes, even on cached runs.
    inspect()
    stages = ["build", "analyze", "validate", "report"] if args.stage == "all" else [args.stage]
    for stage in stages:
        if stage == "inspect": continue
        if stage == "build":
            inputs = [HERE / x for x in ["common.py", "classifiers.py", "matching.py", "build_dataset.py"]] + [OUT / "inspection" / "input_manifest.json"]
            required = [OUT / "analysis_dataset.parquet"] + [OUT / "intermediate" / f"{x}.parquet" for x in ["classified_files", "spec_pr_links", "all_pr_observations", "spec_snapshots", "text_features"]] + [OUT / "validation" / "test_file_review_sample.csv"]
            from build_dataset import build
            action = build
        elif stage == "analyze":
            inputs = [HERE / "analyze.py", HERE / "common.py", OUT / "analysis_dataset.parquet", OUT / "intermediate" / "all_pr_observations.parquet"]
            required = [OUT / "tables" / f"{x}.csv" for x in ["association_tests", "testing_rates", "logistic_regression"]] + [OUT / "figures" / "test_addition_rates.png", OUT / "figures" / "clustered_rate_differences.png"]
            from analyze import analyze
            action = analyze
        elif stage == "validate":
            result = subprocess.run([sys.executable, "-m", "pytest", str(HERE / "tests"), "-q", f"--junitxml={OUT / 'validation' / 'unit_tests.xml'}"], cwd=HERE, text=True, capture_output=True)
            log = result.stdout + result.stderr
            (OUT / "validation" / "unit_test_results.txt").write_text(log, encoding="utf-8")
            print(log)
            if result.returncode:
                raise RuntimeError("Unit tests failed; see outputs/validation/unit_test_results.txt")
            from validate import validate
            validate()
            continue
        else:
            from report import report
            report()
            continue
        sig = signature(inputs)
        old = state.get(stage, {})
        intact = all(p.exists() for p in required)
        intact = intact and old.get("output_manifest_version") == 2 and all((OUT / name).exists() and sha256(OUT / name) == digest for name, digest in old.get("outputs", {}).items())
        if not args.force and old.get("signature") == sig and intact:
            print(f"Using validated cache for {stage}")
        else:
            print(f"Running {stage}", flush=True)
            action()
            # Fingerprint all outputs belonging to the stage to detect tampering/deletion.
            outputs = stage_outputs(stage)
            state[stage] = {"signature": sig, "output_manifest_version": 2, "outputs": {p.relative_to(OUT).as_posix(): sha256(p) for p in outputs}}
            write_json(statepath, state)


if __name__ == "__main__":
    main()
