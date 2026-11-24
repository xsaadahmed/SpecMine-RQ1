import json,shutil
from common import OUT,CACHE,sha256,write_json
D=OUT/'full_cohort/incident_progress';D.mkdir(exist_ok=True)
manifest=D/'preserved_manifest.json'
if not manifest.exists():
 sources=[p for p in (OUT/'full_cohort').rglob('*') if p.is_file() and not p.is_relative_to(D)]
 write_json(manifest,{str(p.relative_to(OUT)):sha256(p.read_bytes()) for p in sources})
 for p in sources:
  target=D/'prior_outputs'/p.relative_to(OUT/'full_cohort');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
window=json.loads((OUT/'full_cohort/circuit_state_source-reference-v3.json').read_text());ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts']
rows=[]
for r in window:
 cached=json.loads((CACHE/'grok'/(r['cache_key']+'.json')).read_text())
 rows.append({**r,'raw_output':cached.get('diagnostic',{}).get('raw_output'),'api_attempt_matches':sum(x['task']==r['cache_key'] for x in ledger),'historical_or_seeded':r['origin']!='live','actual_original_attempt_at':[x['at'] for x in ledger if x['task']==r['cache_key']]})
write_json(D/'trigger_window.json',rows);write_json(D/'api_cost.json',{'attempts':len(ledger),'cost':sum(x.get('reported_cost_usd',0) for x in ledger),'input_tokens':sum(x.get('usage',{}).get('prompt_tokens',0) for x in ledger),'output_tokens':sum(x.get('usage',{}).get('completion_tokens',0) for x in ledger)})
print(json.dumps({'attempts':len(ledger),'cost':sum(x.get('reported_cost_usd',0) for x in ledger),'window_unique_keys':len({x['cache_key'] for x in window}),'window_failed':sum(x['failed'] for x in window),'new_full_cohort_attempts':len(ledger)-43},indent=2))
