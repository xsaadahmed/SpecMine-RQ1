"""Explicit second smoke batch: failed files only, never more than 20 lifetime attempts."""
import argparse,csv,json,os
import portalocker
import grok
from common import HERE,HIST,OUT,CACHE,sha256,write_json,protect_prior
from detector import language

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');a=p.parse_args()
    from cohort_overlay import reference_trial_required
    if a.live and reference_trial_required(OUT/'full_cohort'):
        p.error('The paid smoke retry is closed. See independent_review.py.')
    if a.live and not os.environ.get('XAI_API_KEY','').strip():
        print('Blocked: XAI_API_KEY unavailable; no paid requests.');return
    failures=[json.loads(p.read_text()) for p in (CACHE/'grok').glob('*.json') if json.loads(p.read_text()).get('status')=='provider_or_validation_failure']
    paths={r['content_sha256']:r['file'] for r in csv.DictReader((OUT/'failure_diagnosis/response_audit.csv').open(encoding='utf-8'))}
    needed={r['content_sha256'] for r in failures};texts={}
    for root in [HIST/'outputs/content',OUT/'content']:
        for f in root.rglob('*'):
            if f.is_file():
                raw=f.read_bytes();h=sha256(raw)
                if h in needed:
                    try:texts[h]=raw.decode('utf-8')
                    except UnicodeDecodeError:pass
    repair=CACHE/'repair_smoke';(repair/'grok').mkdir(parents=True,exist_ok=True)
    grok.CACHE=repair
    b=grok.Budget(max_requests=20,max_spend=3,repair_batch=True)
    resolver=grok.GrokResolver(dry_run=not a.live,budget=b)
    rows=[]
    for r in failures:
        h=r['content_sha256'];path=paths[h]
        result=resolver.resolve(texts[h],path,language(path),h) if h in texts else {'status':'source_not_found','classification':'uncertain'}
        rows.append({'path':path,'content_sha256':h,**result})
    write_json(OUT/'failure_diagnosis/repair_results.json',rows)
    write_json(OUT/'failure_diagnosis/repair_usage.json',grok.usage_report(b))
    protect_prior()
    print(json.dumps({'live':a.live,'results':[{'path':r['path'],'status':r['status']} for r in rows],'lifetime_attempts':len(b.state['attempts'])},indent=2))
if __name__=='__main__':
    with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):main()
