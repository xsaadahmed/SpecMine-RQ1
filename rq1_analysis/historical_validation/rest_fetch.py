"""Optional portable REST acquisition; the executed pilot used the GitHub connector."""
import argparse
from datetime import datetime,timezone
import json
import os
import time

import requests

from hv_common import CACHE, cached, write_json
from plan import all_requests


FILE_KEYS=["filename","previous_filename","status","sha","additions","deletions","changes"]


def files(rows):return [{k:f[k] for k in FILE_KEYS if k in f} for f in rows]


def normalize(kind,d):
    if kind=="metadata":
        keys=["number","state","merged","created_at","closed_at","merged_at","updated_at","commits","changed_files","additions","deletions","merge_commit_sha"]
        out={k:d.get(k) for k in keys}
        out.update(head_sha=d["head"]["sha"],base_sha=d["base"]["sha"],head_repo_full_name=(d["head"].get("repo") or {}).get("full_name"),url=d.get("html_url"))
        return out
    if kind=="content":return {"content":d["content"],"encoding":d["encoding"],"sha":d["sha"],"display_url":d["html_url"]}
    if kind=="files":return files(d)
    if kind=="commits":return [{"sha":c["sha"],"parents":[p["sha"] for p in c["parents"]],"authored_at":c["commit"]["author"]["date"],"committed_at":c["commit"]["committer"]["date"]} for c in d]
    if kind=="commit":return {"sha":d["sha"],"parents":[p["sha"] for p in d["parents"]],"committed_at":d["commit"]["committer"]["date"],"files":files(d["files"]),"files_may_be_truncated":len(d["files"])>=100}
    raise ValueError(kind)


def fetch_stage(stage,limit,delay):
    session=requests.Session()
    session.headers.update({"Accept":"application/vnd.github+json","User-Agent":"CS520-SpecMine-historical-pilot","X-GitHub-Api-Version":"2022-11-28"})
    token=os.environ.get("GITHUB_TOKEN")
    if token:session.headers["Authorization"]="Bearer "+token
    for _ in range(limit):
        unique={r["id"]:r for r in all_requests(stage)}
        pending=[r for r in unique.values() if cached(r) is None]
        if not pending:print(f"No pending {stage} requests");return
        req=pending[0];kind=req["kind"];args=req["args"]
        if kind=="metadata":url=f"https://api.github.com/repos/{args['repository_full_name']}/pulls/{args['pr_number']}"
        elif kind=="content":
            from urllib.parse import quote
            url=f"https://api.github.com/repos/{args['repository_full_name']}/contents/{quote(args['path'],safe='/')}?ref={args['ref']}"
        else:url=args["url"]
        response=session.get(url,timeout=45)
        if response.status_code==429 or (response.status_code==403 and (response.headers.get("X-RateLimit-Remaining")=="0" or "rate limit" in response.text.lower())):
            raise RuntimeError("GitHub rate limit reached; stop and resume after reset. No error cache or snapshot fallback was written.")
        record={"request":req,"retrieved_at":datetime.now(timezone.utc).isoformat(),"transport":"GitHub REST via requests"}
        if response.ok:
            try:record.update(ok=True,data=normalize(kind,response.json()))
            except (ValueError,KeyError,TypeError) as e:record.update(ok=False,error="normalization_failed",detail=str(e))
        else:record.update(ok=False,error="http_error",detail=f"GitHub HTTP {response.status_code}; no content invented")
        write_json(CACHE/(req["id"]+".json"),record,immutable=True)
        print(kind,req["id"],"ok" if record["ok"] else record["error"])
        remaining=response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining)<=10:raise RuntimeError("Stopping with at most ten API requests remaining; resume after reset")
        time.sleep(delay)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=["metadata","files","commits","anchor","head_content","earlier_content","review_content"]);p.add_argument("--limit",type=int,default=80);p.add_argument("--delay",type=float,default=1.0)
    args=p.parse_args();fetch_stage(args.stage,args.limit,max(1.0,args.delay))
