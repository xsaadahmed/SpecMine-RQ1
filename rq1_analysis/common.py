"""Paths and small I/O utilities. All writes are contained in this project."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data"
OUT = HERE / "outputs"
for name in ["inspection", "intermediate", "tables", "figures", "validation"]:
    (OUT / name).mkdir(parents=True, exist_ok=True)

FEATURES = ["has_acceptance_criteria", "has_edge_cases", "has_requirements", "n_words"]
KEY = ["repo_name", "pr_number"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding="utf-8")


def save(df, name, folder="tables"):
    df.to_csv(OUT / folder / f"{name}.csv", index=False)


def cache(df, name):
    df.to_parquet(OUT / "intermediate" / f"{name}.parquet", index=False)
