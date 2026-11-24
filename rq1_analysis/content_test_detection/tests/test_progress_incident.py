import json
import pytest
import grok,scale100 as e,full_cohort as f
from common import OUT,CACHE,sha256
from detector import eligible,classify
D=OUT/'full_cohort/incident_progress'

@pytest.mark.parametrize('row',json.loads((D/'trigger_window.json').read_text()),ids=lambda r:r['path'])
def test_exact_breaker_window_responses(row):
 r=json.loads((CACHE/'grok'/(row['cache_key']+'.json')).read_text())
 assert r.get('finish_reason',r.get('diagnostic',{}).get('finish_reason'))=='REASON_STOP'
 text=(OUT/'content'/(row['hash']+'.txt')).read_text(encoding='utf-8-sig')
 if r['status']=='validated':grok.validate_cached_classification(r,text)
 elif not row['failed']:grok.validate_output(r['diagnostic']['raw_output'],grok.sanitize(text)[0])
 elif r.get('diagnostic',{}).get('raw_output'):
  with pytest.raises(ValueError):grok.validate_output(r['diagnostic']['raw_output'],grok.sanitize(text)[0])

def test_required_reference_wire_schema_preserves_unknowns():
 assert grok.WireClassification.model_json_schema()['properties']['evidence']['minItems']==1
 value={'classification':'not_test','has_executable_tests':False,'language':'Swift','evidence':[],'reason':'production','needs_review':False}
 with pytest.raises(ValueError):grok.WireClassification.model_validate(value)
 with pytest.raises(ValueError):grok.validate_output(value,'struct Production {}')

def test_monitor_excludes_seeded_history_other_prompts_and_duplicates(tmp_path):
 path=tmp_path/'window.json'
 data=[{'cache_key':'old','origin':'offline_revalidated_live_response','prompt_version':grok.PROMPT_VERSION,'failed':True,'repo':'old'},{'cache_key':'old2','origin':'live','prompt_version':'old','failed':True,'repo':'old'}]+[{'cache_key':'new','origin':'live','prompt_version':grok.PROMPT_VERSION,'failed':False,'repo':'new'}]*2
 path.write_text(json.dumps(data))
 r=e.Resolver(budget=grok.Budget(tmp_path/'ledger.json'),circuit_path=path)
 assert len(r.recent_results)==1 and r.recent_results[0]['cache_key']=='new'

def test_ignore_files_are_not_executable_candidates():
 assert not eligible('editors/vscode/.vscodeignore')
 assert eligible('tests/script.ps1')

@pytest.mark.parametrize('source',[
 'public class TestSuite { [Fact] public void Valid() { Assert.True(1 == 1); } }',
 'using AwesomeAssertions; [TestClass] public class Cases { [TestMethod] public void Valid() { (1).Should().Be(1); } }'])
def test_global_test_imports_do_not_hide_implemented_tests(source):
 assert classify(source,'Cases.cs')['classification']=='automated_test'

def test_annotation_without_framework_context_is_uncertain():
 assert classify('class Cases { [Fact] public void Possible() { UnknownAction(); } }','Cases.cs')['classification']=='uncertain'

def test_ledger_did_not_change_and_prior_outputs_archived():
 ledger=json.loads((OUT/'api_ledger.json').read_text())['attempts'];original=json.loads((D/'api_cost.json').read_text());assert len(ledger)>=original['attempts']
 assert sum(x.get('reported_cost_usd',0) for x in ledger[:original['attempts']])==pytest.approx(original['cost'])
 manifest=json.loads((D/'preserved_manifest.json').read_text())
 assert all(sha256((D/'prior_outputs'/p.replace('\\','/').removeprefix('full_cohort/')).read_bytes())==h for p,h in manifest.items())

def test_actual_csharp_global_import_regression_cases():
 correction=json.loads((OUT/'full_cohort/known_negative_corrections.json').read_text())[0]
 text=(OUT/'content'/(correction['file_content_hash']+'.txt')).read_text(encoding='utf-8-sig')
 assert classify(text,correction['confirmed_file_path'])['classification']=='automated_test'

def test_quoted_assertions_and_skipped_annotations_are_not_positive():
 assert classify('class Cases { [Fact] public void Possible() { Print("Assert.True(1)"); } }','Cases.cs')['classification']=='uncertain'
 assert classify('class Cases { [Fact(Skip="disabled")] public void DisabledCase() { Assert.True(1 == 1); } }','Cases.cs')['classification']=='uncertain'

def test_progress_distinguishes_unexamined_pending_blocked_and_resolved():
 import pandas as pd
 states=pd.read_csv(D/'progress_states.csv')
 assert len(states)==500
 assert states.resumable.sum()==484
 assert states.actionable_now.sum()==483
 assert states.verification_state.eq('not_yet_examined').sum()==483
 assert states.verification_state.eq('exhaustively_verified_negative').sum()==9

def test_verified_negative_correction_is_published_with_pinned_proof(tmp_path,monkeypatch):
 import pandas as pd
 monkeypatch.setattr(f,'DEST',tmp_path);monkeypatch.setattr(f,'BATCH','batch_0001')
 (tmp_path/'batch_0001/results').mkdir(parents=True);(tmp_path/'batch_0001/audits').mkdir()
 correction=(OUT/'full_cohort/known_negative_corrections.json').read_bytes()
 (tmp_path/'known_negative_corrections.json').write_bytes(correction)
 entry=pd.read_csv(D/'offline_main_outcomes.csv');sample=pd.read_csv(OUT/'full_cohort/batch_0001/sample.csv')
 f.publish(entry,sample)
 current=pd.read_csv(tmp_path/'current_main_outcomes.csv')
 row=current[current.repo_name.eq('unoplatform/uno')&current.pr_number.eq(23046)].iloc[0]
 assert row.test_added_content_verified==1 and row.pinned_commit_sha
