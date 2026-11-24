import json
from pathlib import Path
import pytest
import full_cohort as f
from common import OUT,sha256

@pytest.mark.parametrize('state,remaining,fetch,model,expected',[
('not_yet_examined',0,True,True,'github_cumulative_limit'),
('waiting_github_content',0,True,False,'github_cumulative_limit'),
('not_yet_examined',1000,True,False,None),
('waiting_grok_classification',0,True,False,'model_requests_disabled_or_unavailable'),
('waiting_grok_classification',0,True,True,None),
('cache_ready_for_replay',0,False,False,None),
('waiting_github_content',1000,False,False,'github_acquisition_not_enabled')])
def test_resource_gate_preserves_cache_work_and_resumes_when_allowance_exists(state,remaining,fetch,model,expected):
 assert f.resource_block_reason(state,remaining,fetch,model)==expected

def test_actual_stalled_run_has_zero_github_allowance():
 d=json.loads((OUT/'full_cohort/incident_no_progress/diagnosis.json').read_text())
 assert d['resources']['github_used']==1500 and d['resources']['github_remaining']==0
 assert d['actionable_partition']=={'github_cumulative_limit':274,'model_requests_disabled_or_unavailable':15}

def test_existing_outputs_and_labels_untouched():
 # Live runs legitimately update current progress; retain the point-in-time
 # preservation result rather than requiring those outputs to freeze forever.
 result=json.loads((OUT/'full_cohort/incident_no_progress/integrity.json').read_text())
 assert result['status']=='passed' and result['new_paid_calls']==0
