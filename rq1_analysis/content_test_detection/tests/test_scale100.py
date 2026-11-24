import json
from pathlib import Path
import pandas as pd
import pytest
import scale100 as s
import grok
from test_grok import GOOD,SOURCE

def test_repaired_prediction_reused_without_transport(tmp_path,monkeypatch):
    monkeypatch.setattr(s,'CACHE',tmp_path)
    path=tmp_path/'repair_smoke/grok';path.mkdir(parents=True)
    h='hash';key=grok.cache_key(h)
    (path/(key+'.json')).write_text(json.dumps({**GOOD,'status':'validated','content_sha256':h,'model':grok.MODEL,'reasoning_effort':grok.REASONING,'cache_key':key,'prompt_version':grok.PROMPT_VERSION}))
    monkeypatch.setattr(s,'BASE',tmp_path)
    r=s.Resolver(transport=lambda *a:pytest.fail('paid call'),budget=grok.Budget(tmp_path/'ledger.json'))
    assert r.resolve(SOURCE,'a.js','javascript',h)['cache_hit']

def test_frozen_sample_is_unique_balanced_and_previously_unknown():
    sample=pd.read_csv(s.DEST/'sample100.csv')
    # The reconciliation table changes as acquisition advances. Compare the
    # frozen pre-scaling main outcomes, not the mutable latest reconciliation.
    rec=pd.read_csv(s.OUT/'main_pr_outcomes.csv')
    assert len(sample)==100 and not sample.duplicated(s.KEY).any()
    assert set(sample.tool)=={'openspec','speckit'}
    joined=sample[s.KEY].merge(rec,on=s.KEY,validate='one_to_one')
    assert joined.test_added_content_verified.isna().all()

def test_powershell_citations_not_silently_rewritten():
    r=json.loads((s.DEST/'powershell_failure_diagnosis.json').read_text())
    assert len(r['citations'])==8
    assert sum(not e['verbatim_present'] for e in r['citations'])==2
