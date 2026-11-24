import ast,copy,json,traceback
import pytest
import grok,scale100 as e,full_cohort as f
from common import OUT
D=OUT/'full_cohort/incident_role'
ROWS=json.loads((D/'window.json').read_text())
@pytest.mark.parametrize('row',ROWS,ids=lambda r:r['path'])
def test_actual_role_window(row):
 text=(OUT/'content'/(row['hash']+'.txt')).read_text(encoding='utf-8-sig');safe,_=grok.sanitize(text)
 if not row['failed']:return
 if row['path'].endswith('.verify-passed'):
  with pytest.raises(ValueError,match='declared role'):grok.validate_output(row['diagnostic']['raw_output'],safe)
 else:assert grok.validate_output(row['diagnostic']['raw_output'],safe).classification=='not_test'

def test_history_revalidated_not_cleared_or_threshold_changed(tmp_path):
 old=tmp_path/'historical_window.json'
 old.write_bytes((D/'window.json').read_bytes())
 r=e.Resolver(circuit_path=old,budget=grok.Budget(tmp_path/'ledger.json'))
 assert len(r.recent_results)==10
 assert len({x['cache_key'] for x in r.recent_results})==10
 assert sum(x['failed'] for x in r.recent_results)==1
 assert sum(x.get('original_failed',False) for x in r.recent_results)==6

def test_real_exception_handler_preserves_original_traceback_and_finalizes():
 tree=ast.parse(__import__('pathlib').Path(f.__file__).read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');block=copy.deepcopy(next(n for n in main.body if isinstance(n,ast.Try)))
 block.body=ast.parse('work()').body;block.finalbody=ast.parse('save()').body
 fn=ast.parse('def run():\n pass').body[0];fn.body=[block];module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));events=[]
 def work():raise LookupError('original failure')
 namespace={'work':work,'save':lambda:events.append('saved'),'write_json':lambda *a:None,'DEST':__import__('pathlib').Path('.'),'GitHubLowQuota':f.GitHubLowQuota}
 exec(compile(module,'actual_exception_handler','exec'),namespace)
 with pytest.raises(LookupError,match='original failure') as caught:namespace['run']()
 assert events==['saved'] and any(frame.name=='work' for frame in traceback.extract_tb(caught.value.__traceback__))
