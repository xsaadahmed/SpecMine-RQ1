from pathlib import Path
for name in ['scale100.py','full_cohort.py','overnight.py','acquire.py']:
 p=Path('rq1_analysis/content_test_detection')/name;s=p.read_text()
 s='from github_http import read_count\n'+s
 s=s.replace("len(list((CACHE/'github').glob('*.json')))",'read_count(CACHE)')
 if name=='scale100.py':
  s=s.replace('resp=session.get(url,timeout=40)','from github_http import get_with_retry\n        resp=get_with_retry(session,url,req,CACHE,github_limit)')
 p.write_text(s)
p=Path('rq1_analysis/content_test_detection/fetch_github.py');s=p.read_text();s=s.replace('response=session.get(url,timeout=40)','from github_http import get_with_retry\n        response=get_with_retry(session,url,req,CACHE,github_limit)');p.write_text(s)
