import pandas as pd
import full_cohort as f,scale100 as e
from common import OUT,BASE,write_json
D=OUT/'full_cohort/incident_progress';candidates=pd.read_csv(D/'negative_annotation_recheck.csv');keys=candidates[candidates.classification.eq('automated_test')][['repo_name','pr_number']].drop_duplicates();main=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet');e.DEST=D/'negative_recheck';(e.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
rows,a,q=e.run_rows(main.merge(keys,on=['repo_name','pr_number']),e.Resolver(dry_run=True))
assert rows.test_added_content_verified.eq(1).all()
rows.to_csv(D/'verified_prior_negative_corrections.csv',index=False)
write_json(OUT/'full_cohort/known_negative_corrections.json',rows.to_dict('records'),immutable=True)
print(rows[['repo_name','pr_number','test_added_content_verified','confirmed_file_path']].to_string(index=False))
