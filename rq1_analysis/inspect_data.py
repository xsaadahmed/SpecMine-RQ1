"""Read every required schema, audit keys/nulls, and fingerprint original inputs."""
import importlib.metadata
import platform
import re
import subprocess

import duckdb
import pandas as pd
import pyarrow.parquet as pq

from common import DATA, FEATURES, OUT, REPO, save, sha256, write_json

TABLE_KEYS = {
    "spec_files": [["file_url_sha16"], ["repo_name", "file_path"]],
    "spec_content_features": [["file_url_sha16"]],
    "pull_requests": [["id"], ["tool", "id"], ["tool", "repo_name", "pr_number"], ["repo_name", "pr_number"]],
    "pr_files": [["id"], ["tool", "id"], ["tool", "repo_name", "pr_number", "file_path"], ["repo_name", "pr_number", "file_path"]],
}


def input_manifest():
    paths = sorted(DATA.glob("*.parquet")) + [REPO / x for x in
        ["specs.jsonl.gz", "kiro_specs.jsonl.gz", "sample_repos.txt", "README.md", "DATA_DICTIONARY.md", "schema.sql", "load.py"]]
    return {str(p.relative_to(REPO)).replace("\\", "/"): {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in paths}


def inspect():
    manifest = input_manifest()
    baseline = OUT / "inspection" / "input_manifest.json"
    if baseline.exists():
        import json
        if json.loads(baseline.read_text()) != manifest:
            raise RuntimeError("Original inputs differ from the saved manifest. Investigate; do not overwrite the baseline.")
    else:
        write_json(baseline, manifest)
    inventory, columns, keys, differences = [], [], [], []
    schema_sql = (REPO / "schema.sql").read_text(encoding="utf-8")
    con = duckdb.connect()
    con.execute("SET threads=2")
    for path in sorted(DATA.glob("*.parquet")):
        table = path.stem
        schema = pq.read_schema(path)
        rows = pq.ParquetFile(path).metadata.num_rows
        inventory.append({"table": table, "rows": rows, "columns": len(schema), "bytes": path.stat().st_size})
        if table not in TABLE_KEYS:
            continue
        view = f"read_parquet('{path.as_posix()}')"
        nulls = con.execute("SELECT " + ",".join(f'SUM(CAST("{c}" IS NULL AS INTEGER))' for c in schema.names) + f" FROM {view}").fetchone()
        for field, missing in zip(schema, nulls):
            columns.append({"table": table, "column": field.name, "arrow_type": str(field.type), "rows": rows, "missing": missing, "missing_fraction": missing / rows})
        for key in TABLE_KEYS[table]:
            quoted = ",".join(f'"{x}"' for x in key)
            groups, excess = con.execute(f"SELECT COUNT(*), COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM {view} GROUP BY {quoted} HAVING COUNT(*)>1)").fetchone()
            keys.append({"table": table, "key": "+".join(key), "duplicate_groups": groups, "excess_rows": excess})
        block = re.search(r"CREATE TABLE `" + table + r"` \((.*?)\) DEFAULT", schema_sql, re.S).group(1)
        declared = re.findall(r"^\s*`([^`]+)`", block, re.M)
        differences.append({"table": table, "sql_columns": len(declared), "actual_columns": len(schema), "extra_in_parquet": sorted(set(schema.names)-set(declared)), "absent_from_parquet": sorted(set(declared)-set(schema.names))})
    save(pd.DataFrame(inventory), "local_inventory", "inspection")
    save(pd.DataFrame(columns), "schemas_and_missingness", "inspection")
    save(pd.DataFrame(keys), "key_uniqueness", "inspection")
    write_json(OUT / "inspection" / "schema_discrepancies.json", differences)
    listed = [line.strip() for line in (REPO / "sample_repos.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    broad = set(pd.read_parquet(DATA / "spec_files.parquet", columns=["repo_name"]).repo_name)
    kiro = set(pd.read_parquet(DATA / "kiro_files.parquet", columns=["repo_name"]).repo_name)
    assert len(listed) == len(set(listed)) and set(listed) == broad | kiro, "Sample repository list differs from local census union"
    write_json(OUT / "inspection" / "sample_repository_coverage.json", {"listed_unique_repositories": len(set(listed)), "broad_census_repositories": len(broad), "kiro_census_repositories": len(kiro), "overlap": len(broad & kiro), "union": len(broad | kiro), "list_matches_local_data": True})
    f = pd.read_parquet(DATA / "spec_content_features.parquet", columns=FEATURES)
    save(f.describe().T.reset_index(names="feature"), "snapshot_feature_descriptives", "inspection")
    versions = {x: importlib.metadata.version(x) for x in ["pandas", "pyarrow", "duckdb", "numpy", "scipy", "statsmodels", "patsy", "matplotlib", "pytest"]}
    write_json(OUT / "inspection" / "environment.json", {"python": platform.python_version(), "packages": versions, "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()})
    print(pd.DataFrame(inventory).to_string(index=False))


if __name__ == "__main__":
    inspect()
