import csv,json
from common import OUT
D=OUT/'full_cohort/incident_progress';rows=json.loads((D/'trigger_window.json').read_text())
with (D/'trigger_window.csv').open('w',encoding='utf-8',newline='') as f:
 fields=['repo','pr','path','origin','status','finish','prompt_version','validator_version','failed','api_attempt_matches','historical_or_seeded','diagnostic']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
