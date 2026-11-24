from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
P=Path(__file__).parent;O=P/'outputs'

def test_join_identity_and_missingness():
 d=pd.read_csv(O/'analysis_dataset.csv');v=json.loads((O/'validation.json').read_text())
 assert len(d)==3186 and not d.duplicated(['repo_name','pr_number']).any()
 assert d.test_added_content_verified.notna().sum()==1864
 assert d.test_added_content_verified.eq(1).sum()==1023 and d.test_added_content_verified.eq(0).sum()==841
 assert v['unmatched_outcomes']==v['unmatched_feature_rows']==0

def test_feature_denominators_exclude_unknown_outcomes():
 d=pd.read_csv(O/'analysis_dataset.csv');r=pd.read_csv(O/'results.csv')
 for row in r.to_dict('records'):
  assert row['present_resolved']+row['absent_resolved']==1864
  assert row['present_positive']+row['absent_positive']==1023
  assert row['present_negative']+row['absent_negative']==841
  assert row['present_unknown']+row['absent_unknown']==1322
  assert np.isclose(row['present_rate'],row['present_positive']/row['present_resolved'])

def test_inputs_and_old_results_unchanged():
 v=json.loads((O/'validation.json').read_text())
 for path,digest in v['source_hashes'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest

def test_regression_estimation_sample_and_rank():
 diagnostics=json.loads((O/'model_diagnostics.json').read_text())
 assert all(x['n']==1864 and x['repositories']==192 and x['stable'] and x['rank']==x['parameters'] for x in diagnostics)

def test_label_change_counts_and_negative_proof():
 v=json.loads((O/'validation.json').read_text())
 assert v['negative_to_positive']==33 and v['positive_to_negative']==11
 assert v['disagreements']==44 and v['negative_inspection_complete_violations']==0 and v['missing_pin_resolved']==0

def test_selection_draws_are_not_duplicated_or_misused_as_completion():
 a=pd.read_csv(O/'selection_assignments.csv');d=pd.read_csv(O/'analysis_dataset.csv')
 assert len(a)==2000 and not a.duplicated(['repo_name','pr_number']).any()
 assert d[d.selection_batch.eq('outside_scaling_batches')].test_added_content_verified.isna().sum()==1031
