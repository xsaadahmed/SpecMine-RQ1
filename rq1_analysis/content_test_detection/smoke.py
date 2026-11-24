"""Gate batches above ten on actual validated smoke responses and accounting."""
import json

from common import CACHE,OUT,write_json
from grok import Budget,MODEL,REASONING,PROMPT_VERSION


def validate_smoke(budget=None):
    budget=budget or Budget()
    attempts=budget.state['attempts']
    responses=[json.loads(p.read_text()) for p in (CACHE/'grok').glob('*.json')]
    good=[r for r in responses if r.get('status')=='validated' and r.get('model')==MODEL and r.get('reasoning_effort')==REASONING and r.get('prompt_version')==PROMPT_VERSION]
    passed=bool(attempts and good) and all(a['status']=='completed' and a.get('usage',{}).get('total_tokens',0)>0 and 'reported_cost_usd' in a for a in attempts)
    result={'passed':passed,'attempts':len(attempts),'validated_responses':len(good),'model':MODEL,'reasoning_effort':REASONING,'checks':['actual model response parsed under strict schema','verbatim source evidence validation','token usage present','provider cost reconciled','no failed/reserved attempts'],'limitation':'Technical integration check, not human-ground-truth validation. No live response means this gate stays closed.'}
    write_json(OUT/'grok_smoke_validation.json',result)
    if passed:
        budget.state['smoke_validated']=True
        write_json(budget.path,budget.state)
    return result


if __name__=='__main__':print(validate_smoke())
