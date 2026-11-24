from pathlib import Path
p=Path('rq1_analysis/content_test_detection/scale100.py');s=p.read_text();s=s.replace("else a['url']", "else f\"https://api.github.com/repos/{a['repository_full_name']}/git/blobs/{a['sha']}\" if kind=='blob' else a['url']")
start=s.index("        if allow_missing_resources and kind=='content' and")
end=s.index('        write_json(CACHE',s.index('            return True',start)+len('            return True'))
s=s[:start]+'''        if kind in {'content','blob'}:
            directory=DEST/'retrieval_diagnostics';directory.mkdir(exist_ok=True)
            write_json(directory/(req['id']+'.json'),{'request':req,'http_status':resp.status_code,'content_type':resp.headers.get('Content-Type'),'response_shape':type(body).__name__,'keys':sorted(body) if isinstance(body,dict) else None,'metadata':{k:body.get(k) for k in ['type','encoding','size','sha'] if k in body} if isinstance(body,dict) else {}})
'''+s[end:]
s=s.replace("'http_status':resp.status_code})", "'http_status':resp.status_code,'request':req,'content_type':resp.headers.get('Content-Type')})")
p.write_text(s)
