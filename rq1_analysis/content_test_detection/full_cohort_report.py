"""Report current coverage without fitting regression or changing old results."""
import json
import pandas as pd
from common import BASE,OUT,CACHE,write_json,protect_prior
D=OUT/'full_cohort';main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet');out=pd.read_csv(D/'current_main_outcomes.csv')
cols=['repo_name','pr_number','test_added_content_verified'];d=main.merge(out[cols],on=['repo_name','pr_number'],validate='one_to_one')
for grouping in ['tool','repo_language','has_acceptance_criteria','has_edge_cases']:
 rows=[]
 for value,g in d.groupby(grouping,dropna=False):
  y=g.test_added_content_verified;rows.append({'group':value,'n':len(g),'positive':int(y.eq(1).sum()),'negative':int(y.eq(0).sum()),'unknown':int(y.isna().sum()),'resolved_fraction':float(y.notna().mean())})
 pd.DataFrame(rows).to_csv(D/('coverage_by_'+grouping+'.csv'),index=False)
ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts']
registry={}
for root in [CACHE/'grok',CACHE/'repair_smoke/grok',CACHE/'offline_revalidated']:
 for p in root.glob('*.json'):
  r=json.loads(p.read_text())
  if r.get('status')=='validated':registry[r['content_sha256']]=r
api={'lifetime_attempts':len(ledger),'input_tokens':sum(x.get('usage',{}).get('prompt_tokens',0) for x in ledger),'output_tokens':sum(x.get('usage',{}).get('completion_tokens',0) for x in ledger),'cumulative_reported_cost_usd':sum(x.get('reported_cost_usd',0) for x in ledger),'unreconciled_cost_reservations':sum('reported_cost_usd' not in x for x in ledger),'unique_validated_contents_all_caches':len(registry),'new_paid_calls':0,'configured_cap_usd':3}
write_json(D/'actual_api_totals.json',api)
write_json(D/'statistical_readiness.json',{'regressions_executed':False,'resolved_n':int(d.test_added_content_verified.notna().sum()),'resolved_repositories':int(d[d.test_added_content_verified.notna()].repo_name.nunique()),'coverage_fraction':float(d.test_added_content_verified.notna().mean()),'judgment':'Insufficient outcome coverage and mixed selection mechanisms; withhold regression. Draw inclusion weights cannot repair outcome-dependent verification. Historical-head exposure cohort remains separate from snapshot predictors.'})
protect_prior();print(json.dumps(api,indent=2))
