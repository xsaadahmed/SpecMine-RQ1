"""No-network audit; preserves live caches, ledger and previous research outputs."""
import csv,json
from pathlib import Path
from common import CACHE,OUT,HERE,HIST,sha256,protect_prior
from grok import validate_output

def main():
    dest=OUT/'failure_diagnosis';dest.mkdir(exist_ok=True)
    mapping={}
    for p in [OUT/'grok_dry_run_plan.json']:
        if p.exists():
            for r in json.loads(p.read_text()):mapping[r['content_sha256']]=r['path']
    for p in OUT.glob('*inspection_audit.csv'):
        for r in csv.DictReader(p.open(encoding='utf-8')):
            h=r.get('content_sha256')
            if h:mapping[h]=r.get('path',r.get('file_path',''))
    rows=[]
    sources={}
    for root in [HIST/'outputs/content',OUT/'content']:
        for p in root.rglob('*'):
            if p.is_file():
                raw=p.read_bytes()
                try:sources[sha256(raw)]=raw.decode('utf-8')
                except UnicodeDecodeError:pass
    for p in sorted((CACHE/'grok').glob('*.json')):
        r=json.loads(p.read_text());failed=r['status']!='validated'
        if not failed:
            from grok import Classification
            validate_output({k:r[k] for k in Classification.model_fields},sources[r['content_sha256']],complete=r.get('complete_input',True))
        kind=r.get('error_type','')
        explanation=('Pydantic ValidationError: JSON/schema/consistency rejection. Original response and detailed errors were discarded; exact cause and attempted class are unrecoverable.' if kind=='ValidationError' else 'ValueError: finish/evidence/context/conflict check rejected output. Original response and message were discarded; exact check and attempted class are unrecoverable.') if failed else 'Original application accepted schema and verbatim evidence; retained classification is available.'
        rows.append({'cache_key':p.stem,'file':mapping.get(r['content_sha256'],'unmapped; see content hash'),'content_sha256':r['content_sha256'],'classification_attempted':'unrecoverable' if failed else r['classification'],'error_type':kind,'failure_reason':explanation,'proposed_fix':'Keep unresolved; bounded retry needs retained response/stage diagnostics and explicit citation instructions' if failed else 'Preserve cached classification; no new request','resolved_offline':False if failed else True})
    with (dest/'response_audit.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    protect_prior()
    print(json.dumps({'responses':len(rows),'failures':sum(not r['resolved_offline'] for r in rows),'offline_recovered':0,'new_paid_calls':0}))
if __name__=='__main__':main()
