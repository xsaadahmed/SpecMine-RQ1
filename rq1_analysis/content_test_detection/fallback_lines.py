import json
from common import OUT,CACHE
from grok import sanitize
w=json.loads((OUT/'full_cohort/incident_fallback/window.json').read_text())
for r in w:
 if not r['failed']:continue
 x=json.loads(r['diagnostic']['raw_output']);t=sanitize((OUT/'content'/(r['hash']+'.txt')).read_text(encoding='utf-8-sig'))[0].splitlines()
 print(r['path'],[(e,t[e['line']-1]) for e in x['evidence']])

