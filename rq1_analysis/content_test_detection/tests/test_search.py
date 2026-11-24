from pipeline import search_pr


def file(path,status='added'):return {'filename':path,'status':status}


def negative(text,row,provenance):return {'classification':'not_test','has_executable_tests':False,'needs_review':False,'method':'deterministic','evidence':[]}


def test_positive_exits_immediately_in_priority_order():
    seen=[]
    def fetch(row):
        seen.append(row['filename']);return 'test',{'commit_sha':'a'*40,'content_sha256':'hash','status':'verified'},None
    def yes(*args):return {'classification':'automated_test','has_executable_tests':True,'needs_review':False,'method':'deterministic','evidence':[{'symbol':'test'}]}
    result,audit,pending=search_pr([file('src/other.py'),file('tests/test_a.py'),file('existing_test.py','modified')],fetch,yes)
    assert result['test_added_content_verified']==1
    assert seen==['tests/test_a.py'] and len(audit)==1 and not pending
    assert result['files_avoided_early_exit']==1


def test_negative_requires_exhaustive_inspection():
    def fetch(row):return 'prod',{'status':'verified'},None
    r,a,_=search_pr([file('a.py'),file('b.rs'),file('tests/test_removed.py','removed')],fetch,negative)
    assert r['test_added_content_verified']==0 and r['n_files_inspected']==2 and r['inspection_complete']
    r,_,_=search_pr([file('a.py')],fetch,negative,file_list_complete=False)
    assert r['test_added_content_verified'] is None


def test_missing_or_ambiguous_files_never_become_negative():
    def missing(row):return None,{'status':'not_cached'},{'id':'pending'}
    r,_,q=search_pr([file('a.py')],missing,negative)
    assert r['test_added_content_verified'] is None and q
    def fetch(row):return 'unknown',{'status':'verified'},None
    def uncertain(*args):return {'classification':'uncertain','has_executable_tests':None,'needs_review':True,'method':'deterministic'}
    assert search_pr([file('a.py')],fetch,uncertain)[0]['test_added_content_verified'] is None


def test_zero_eligible_sources_and_modified_tests():
    def forbidden(*args):raise AssertionError('No file should be fetched')
    r,_,_=search_pr([file('test.py','modified'),file('spec.md')],forbidden,forbidden)
    assert r['test_added_content_verified']==0 and r['n_files_inspected']==0


def test_failed_early_file_does_not_hide_later_positive():
    def fetch(row):return (None,{'status':'retrieval_failed'},None) if row['filename']=='tests/a.py' else ('ok',{'status':'verified'},None)
    def yes(*args):return {'classification':'automated_test','has_executable_tests':True,'needs_review':False,'method':'Grok','evidence':['ok']}
    r,_,_=search_pr([file('tests/a.py'),file('tests/b.py')],fetch,yes)
    assert r['test_added_content_verified']==1 and r['n_files_inspected']==1
