"""Optional portable Python acquisition; the executed run used connected GitHub."""
from datetime import datetime,timezone
import os
import time
import re
from urllib.parse import quote

import requests

from acquire import plan
from common import CACHE,write_json

MAX_CONTENT_BYTES=8*1024*1024

def normalize_content(d,blob=False):
    unavailable=lambda reason,**extra:{'unavailable_reason':reason,**extra}
    if isinstance(d,list):return unavailable('directory_listing')
    if not isinstance(d,dict):return unavailable('unexpected_response_type')
    if d.get('submodule_git_url') or d.get('type')=='submodule':return unavailable('submodule_commit_not_source_blob')
    if isinstance(d.get('entries'),list):return unavailable('directory_listing')
    if d.get('type') in {'dir','symlink'} or isinstance(d.get('target'),str):return unavailable('directory' if d.get('type')=='dir' else 'symlink_not_followed')
    if 'message' in d and not d.get('sha'):return unavailable('api_error_object')
    sha=d.get('sha');size=d.get('size');content=d.get('content');encoding=d.get('encoding')
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{40}',sha):return unavailable('missing_or_invalid_blob_sha')
    if isinstance(size,int) and size>MAX_CONTENT_BYTES:return unavailable('local_content_size_limit',sha=sha,size=size)
    if encoding=='base64' and isinstance(content,str) and (content.strip() or size==0):
        return {'content':content,'encoding':'base64','sha':sha,'size':size,'display_url':d.get('html_url')}
    return unavailable('blob_fallback_required' if not blob else 'invalid_blob_response',sha=sha,size=size)


def normalize(kind,d):
    if kind=='metadata':
        fields=['number','state','merged','created_at','closed_at','merged_at','updated_at','merge_commit_sha','commits','changed_files','additions','deletions']
        v={k:d.get(k) for k in fields}
        v.update(head_sha=d['head']['sha'],base_sha=d['base']['sha'],head_repo_full_name=(d['head'].get('repo') or {}).get('full_name'),url=d.get('html_url'));return v
    if kind=='files':return [{k:f[k] for k in ['filename','previous_filename','status','sha','additions','deletions','changes'] if k in f} for f in d]
    if kind in {'content','blob'}:return normalize_content(d,blob=kind=='blob')
    raise ValueError('Unsupported acquisition kind')


def fetch(scope,github_limit=200):
    session=requests.Session();session.headers.update({'Accept':'application/vnd.github+json','User-Agent':'CS520-content-test-detector','X-GitHub-Api-Version':'2022-11-28'})
    if os.environ.get('GITHUB_TOKEN'):session.headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    while True:
        q=plan(scope,limit=1,github_limit=github_limit)
        if not q['requests']:return q
        req=q['requests'][0];args=req['args'];kind=req['kind']
        if kind=='metadata':url=f"https://api.github.com/repos/{args['repository_full_name']}/pulls/{args['pr_number']}"
        elif kind=='content':url=f"https://api.github.com/repos/{args['repository_full_name']}/contents/{quote(args['path'],safe='/')}?ref={args['ref']}"
        elif kind=='blob':url=f"https://api.github.com/repos/{args['repository_full_name']}/git/blobs/{args['sha']}"
        else:url=args['url']
        from github_http import get_with_retry
        response=get_with_retry(session,url,req,CACHE,github_limit)
        if response.status_code==429 or response.status_code==403 and ('rate limit' in response.text.lower() or response.headers.get('X-RateLimit-Remaining')=='0'):
            return {'status':'github_rate_limit_resume_later'}
        record={'request':req,'retrieved_at':datetime.now(timezone.utc).isoformat(),'transport':'GitHub REST Python'}
        if response.ok:
            try:record.update(ok=True,data=normalize(kind,response.json()))
            except (ValueError,KeyError,TypeError):record.update(ok=False,error='invalid_or_oversized_response')
        else:record.update(ok=False,error='http_'+str(response.status_code))
        write_json(CACHE/'github'/(req['id']+'.json'),record,immutable=True)
        if int(response.headers.get('X-RateLimit-Remaining','100'))<=10:return {'status':'github_low_remaining_quota'}
        time.sleep(1)
