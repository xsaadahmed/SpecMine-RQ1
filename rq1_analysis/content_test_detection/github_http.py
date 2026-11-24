"""Bounded transient GET retries; credentials and response bodies are never logged."""
import time
from datetime import datetime,timezone
import requests
from common import write_json

TRANSIENT={500,502,503,504}


class GitHubLowQuota(RuntimeError):
 def __init__(self):
  super().__init__('github_low_quota')


def read_count(cache):
 return len(list((cache/'github').glob('*.json')))+len(list((cache/'github_transient_attempts').glob('*.json')))

def get_with_retry(session,url,request,cache,limit):
 for attempt in range(3):
  if read_count(cache)>=limit:raise RuntimeError('github_request_limit')
  response=None
  try:response=session.get(url,timeout=40)
  except (requests.Timeout,requests.ConnectionError):pass
  if response is not None and response.status_code not in TRANSIENT:return response
  directory=cache/'github_transient_attempts';directory.mkdir(exist_ok=True)
  write_json(directory/(str(time.time_ns())+'.json'),{'request':request,'attempt':attempt+1,'http_status':response.status_code if response is not None else None,'category':'transient_server_or_network_error','at':datetime.now(timezone.utc).isoformat()})
  if attempt==2:raise RuntimeError('github_transient_failure_after_3_attempts; checkpoint preserved')
  retry_after=response.headers.get('Retry-After') if response is not None else None
  if retry_after and not retry_after.isdigit():raise RuntimeError('github_retry_after_requires_review')
  delay=max(2**attempt,int(retry_after or 0))
  if delay>60:raise RuntimeError('github_retry_after_exceeds_bounded_wait')
  time.sleep(delay)
