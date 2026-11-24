"""Build bounded connector acquisition queues; cached failures remain explicit."""
import argparse
import json

import pandas as pd

from hv_common import BASELINE, OUT, api_req, cached, content_req, data_for, pr_req, request


def pilot():
    return pd.read_csv(OUT / "pilot_sample.csv")


def full_list(repo, number, kind):
    meta = data_for(pr_req(repo, number))
    if not meta: return None
    total = meta["changed_files" if kind == "files" else "commits"]
    cap = 3000 if kind == "files" else 250
    if total is None or total > cap: return None
    result = []
    for page in range(1, (total + 99)//100 + 1):
        rows = data_for(api_req(kind, repo, number, page=page))
        if rows is None: return None
        result.extend(rows)
    if len(result) != total: return None
    return result


def is_implementation(path):
    from hv_common import FROZEN
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    dirs = set(x.lower() for x in p.parts[:-1])
    if dirs & FROZEN.SPEC_DIRS: return False
    if "specs" in dirs and p.suffix.lower() in {".md", ".txt"}: return False
    # Include test and fixture code: an anchor after tests were added is too late.
    return p.suffix.lower() in FROZEN.SOURCE_EXTENSIONS


def anchor(repo, number, budget=12):
    """Do not infer precedence from dates or commit messages."""
    commits = full_list(repo, number, "commits")
    if commits is None: return {"status": "commit_list_unavailable_or_incomplete"}
    if not commits: return {"status": "empty_commit_history"}
    previous = None
    inspected = []
    for c in commits[:budget]:
        sha = c["sha"]
        req = api_req("commit", repo, sha=sha)
        detail = data_for(req)
        if not detail:
            return {"status": "need_commit_detail" if cached(req) is None else "commit_detail_inaccessible", "request": req, "inspected": inspected}
        parents = detail.get("parents", [])
        if len(parents) != 1 or (previous is not None and parents[0] != previous):
            return {"status": "nonlinear_history_prefix", "inspected": inspected}
        # A full 100-entry page may be truncated; never use it for precedence.
        if detail.get("files_may_be_truncated"):
            return {"status": "commit_files_possibly_truncated", "inspected": inspected}
        changed = detail.get("files", [])
        implementation_paths = [x["filename"] for x in changed if is_implementation(x["filename"])]
        inspected.append(sha)
        if implementation_paths:
            return {"status": "anchor_established", "anchor_sha": parents[0], "first_implementation_sha": sha, "inspected_prefix": inspected, "earlier_commits_without_detected_executable_changes": len(inspected)-1, "implementation_path_count": len(implementation_paths), "implementation_path_examples": implementation_paths[:5], "scope": "before first observed executable source/test change in verified linear PR prefix", "genuine_preimplementation_proven": False}
        previous = sha
    return {"status": "prefix_budget_exhausted" if len(commits)>budget else "no_observed_implementation_commit", "inspected": inspected}


def active_links():
    l = pd.read_parquet(BASELINE / "outputs/intermediate/spec_pr_links.parquet")
    return l[l.active_spec_change].merge(pilot()[["pilot_id", "repo_name", "pr_number"]], on=["repo_name", "pr_number"], validate="many_to_one")


def resolved_specs():
    records = []
    for row in active_links().to_dict("records"):
        repo, num = row["repo_name"], row["pr_number"]
        files = full_list(repo, num, "files")
        meta = data_for(pr_req(repo, num))
        row["resolved_path"] = None
        row["head_blob_sha_expected"] = None
        if not meta or files is None:
            row["resolution_status"] = "metadata_or_file_list_unavailable"
        else:
            exact = [f for f in files if f["filename"] == row["file_path"]]
            renamed = [f for f in files if f.get("previous_filename") == row["file_path"]]
            candidates = exact or renamed
            if len(candidates) != 1:
                row["resolution_status"] = "path_not_in_live_net_diff" if not candidates else "ambiguous_api_rename"
            else:
                f = candidates[0]
                row["live_status"] = f["status"]
                row["previous_filename"] = f.get("previous_filename")
                row["resolved_path"] = f["filename"]
                row["head_blob_sha_expected"] = f.get("sha")
                row["resolution_status"] = "removed_at_head" if f["status"] == "removed" else "exact_live_path" if exact else "api_previous_filename"
        records.append(row)
    return records


def all_requests(stage):
    rows = pilot()
    if stage == "metadata":
        return [pr_req(r.repo_name, r.pr_number) for r in rows.itertuples()]
    if stage in ["files", "commits"]:
        requests = []
        for r in rows.itertuples():
            meta = data_for(pr_req(r.repo_name, r.pr_number))
            if meta:
                total = meta["changed_files" if stage == "files" else "commits"]
                cap = 3000 if stage == "files" else 250
                if total is not None and total <= cap:
                    requests.extend(api_req(stage, r.repo_name, r.pr_number, page=p) for p in range(1,(total+99)//100+1))
        return requests
    if stage == "anchor":
        return [a["request"] for r in rows.itertuples() if (a:=anchor(r.repo_name,r.pr_number)).get("status") == "need_commit_detail"]
    if stage in ["head_content", "earlier_content"]:
        reqs = []
        for r in resolved_specs():
            if r["resolution_status"] not in ["exact_live_path", "api_previous_filename"]: continue
            meta = data_for(pr_req(r["repo_name"], r["pr_number"]))
            sha, path = meta["head_sha"], r["resolved_path"]
            if stage == "earlier_content":
                a = anchor(r["repo_name"],r["pr_number"])
                if a.get("status") != "anchor_established": continue
                sha = a["anchor_sha"]
                # For a net rename, probe only its actual API-supplied previous path.
                path = r.get("previous_filename") or path
            reqs.append(content_req(r["repo_name"],sha,path))
        return reqs
    if stage == "review_content":
        path = OUT / "review_sample_plan.csv"
        if not path.exists(): return []
        return [content_req(r.content_repo,r.commit_sha,r.content_path) for r in pd.read_csv(path).itertuples() if isinstance(r.commit_sha,str)]
    raise ValueError(stage)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["metadata","files","commits","anchor","head_content","earlier_content","review_content"])
    p.add_argument("--limit",type=int,default=8)
    args=p.parse_args()
    unique={r["id"]:r for r in all_requests(args.stage)}
    pending=[r for r in unique.values() if cached(r) is None]
    print(json.dumps({"stage":args.stage,"total_requests":len(unique),"pending":len(pending),"requests":pending[:args.limit]}))
