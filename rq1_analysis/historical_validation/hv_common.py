"""Isolated paths, immutable caches, and baseline protection for the pilot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent
REPO = BASELINE.parent
OUT = HERE / "outputs"
CACHE = HERE / "cache" / "responses"
for p in [OUT, CACHE, OUT / "content", OUT / "tables", OUT / "figures", HERE / "tests"]:
    p.mkdir(parents=True, exist_ok=True)
KEY = ["repo_name", "pr_number"]
FEATURES = ["has_acceptance_criteria", "has_edge_cases", "has_testing_requirement"]
SEED = "CS520-RQ1-historical-pilot-v1-20261102"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


def write_json(path, obj, immutable=False):
    text = json.dumps(obj, indent=2, ensure_ascii=False, default=str, allow_nan=False)
    if immutable and path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(text):
            raise RuntimeError(f"Refusing to overwrite immutable record {path.name}")
        return
    path.write_text(text, encoding="utf-8")


def protect_baseline():
    manifest = json.loads((HERE / "baseline_manifest.json").read_text(encoding="utf-8"))
    for name, entry in manifest.items():
        path = REPO / name
        assert path.exists() and path.stat().st_size == entry["bytes"] and digest(path) == entry["sha256"], f"Baseline changed: {name}"
    return len(manifest)


def load_baseline_classifier():
    spec = importlib.util.spec_from_file_location("frozen_midpoint_classifiers", BASELINE / "classifiers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FROZEN = load_baseline_classifier()


def request(kind, args):
    ident = hashlib.sha256(json.dumps({"kind": kind, "args": args}, sort_keys=True).encode()).hexdigest()[:24]
    return {"id": ident, "kind": kind, "args": args}


def cached(req):
    path = CACHE / (req["id"] + ".json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def data_for(req):
    r = cached(req)
    return r.get("data") if r and r.get("ok") else None


def pr_req(repo, number):
    return request("metadata", {"repository_full_name": repo, "pr_number": int(number)})


def api_req(kind, repo, number=None, sha=None, page=1):
    endpoint = f"commits/{sha}" if kind == "commit" else f"pulls/{int(number)}/{kind}"
    return request(kind, {"url": f"https://api.github.com/repos/{repo}/{endpoint}?per_page=100&page={page}"})


def content_req(repo, sha, path):
    import re
    assert re.fullmatch(r"[0-9a-f]{40}", str(sha)), "Content must be pinned to full commit SHA"
    return request("content", {"repository_full_name": repo, "ref": sha, "path": FROZEN.normalize_path(path), "encoding": "base64"})


def hash_order(value):
    return hashlib.sha256((SEED + "|" + value).encode()).hexdigest()
