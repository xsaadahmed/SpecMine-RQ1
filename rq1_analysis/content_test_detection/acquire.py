from github_http import read_count
"""Bounded read-only GitHub frontier. Network transport is provided separately."""
import argparse
import json

import pandas as pd

from common import BASE,CACHE,HIST,OUT,write_json
from detector import eligible,priority
from grok import GrokResolver
from pipeline import process_prs,save_grok_plan
from storage import Store

DEFAULT_GITHUB_LIMIT=200


def resource_estimate():
    main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    f=pd.read_parquet(BASE/'outputs/intermediate/classified_files.parquet',columns=['repo_name','pr_number','file_path','change_status'])
    f=f.merge(main[['repo_name','pr_number','tool']],on=['repo_name','pr_number'],validate='many_to_one')
    added=f[f.change_status.eq('added')].copy()
    added['eligible']=added.file_path.map(eligible)
    possible=added[added.eligible]
    pilot=pd.read_csv(HIST/'outputs/pilot_sample.csv')
    review=pd.read_csv(HIST/'outputs/human_review.csv')
    estimate={'cohort_prs':len(main),'historical_pilot_prs':len(pilot),'main_added_files':len(added),'main_eligible_added_source_files':len(possible),'main_prs_with_eligible_additions':len(possible.drop_duplicates(['repo_name','pr_number'])),'worst_case_metadata_requests':len(main),'worst_case_file_page_requests':int(((main.n_files+99)//100).sum()),'worst_case_content_requests':len(possible),'lower_bound_grok_requests':0,'worst_case_grok_requests':len(possible),'grok_smoke_request_cap':10,'grok_initial_spend_cap_usd':3.0,'github_new_request_cap':DEFAULT_GITHUB_LIMIT,'scope_note':'Bounds, not a prediction: early exit, content reuse and deterministic classification reduce requests. All unprocessed PRs remain unknown. The 56-file review sample is stratified, so its ambiguity fraction is not a population forecast.','next_acquisition_plan':'40-PR frontier first; then a frozen diverse 24-PR main-cohort subset, within the total GitHub cap. No bulk 3186-PR acquisition launched.','grok_token_scenarios':{str(n):{'assumed_input_tokens_each':10000,'output_cap_each':1200,'estimated_token_cost_usd':n*(10000*1.25+1200*2.50)/1e6} for n in [10,100,1000]},'credential_status':'Read from environment only; no paid requests when missing'}
    write_json(OUT/'resource_estimate.json',estimate)
    return estimate


def plan(scope,limit=8,github_limit=DEFAULT_GITHUB_LIMIT):
    used=read_count(CACHE)
    if used>=github_limit:return {'scope':scope,'used':used,'budget':github_limit,'requests':[],'status':'github_request_limit'}
    g=GrokResolver(dry_run=True)
    _,queue=process_prs(scope,g)
    save_grok_plan(g)
    return {'scope':scope,'used':used,'budget':github_limit,'pending_frontiers':len(queue),'requests':queue[:min(limit,github_limit-used)],'status':'pending' if queue else 'no_pending_frontiers'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scope',choices=['pilot','main']);p.add_argument('--limit',type=int,default=8);p.add_argument('--github-limit',type=int,default=DEFAULT_GITHUB_LIMIT)
    args=p.parse_args();print(json.dumps(plan(args.scope,args.limit,args.github_limit)))
