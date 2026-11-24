import plan


def stub(monkeypatch,details):
    monkeypatch.setattr(plan,'full_list',lambda *args:[{'sha':x} for x in details])
    monkeypatch.setattr(plan,'api_req',lambda kind,repo,sha:{'id':sha})
    monkeypatch.setattr(plan,'data_for',lambda req:details.get(req['id']))


def test_anchor_is_parent_of_first_code_not_pr_base_or_head(monkeypatch):
    stub(monkeypatch,{'draft':{'parents':['base'],'files':[{'filename':'specs/a/spec.md'}]},'code':{'parents':['draft'],'files':[{'filename':'src/main.py'}]}})
    a=plan.anchor('a/b',1)
    assert a['status']=='anchor_established' and a['anchor_sha']=='draft'
    assert a['first_implementation_sha']=='code'
    assert not a['genuine_preimplementation_proven']


def test_test_code_already_counts_as_implementation(monkeypatch):
    stub(monkeypatch,{'test':{'parents':['base'],'files':[{'filename':'tests/test_a.py'}]}})
    assert plan.anchor('a/b',1)['anchor_sha']=='base'


def test_merge_and_broken_ancestry_withhold_precedence(monkeypatch):
    stub(monkeypatch,{'draft':{'parents':['base'],'files':[{'filename':'spec.md'}]},'merge':{'parents':['draft','other'],'files':[]}})
    assert plan.anchor('a/b',1)['status']=='nonlinear_history_prefix'
    stub(monkeypatch,{'draft':{'parents':['base'],'files':[]},'code':{'parents':['unrelated'],'files':[{'filename':'a.py'}]}})
    assert plan.anchor('a/b',1)['status']=='nonlinear_history_prefix'


def test_truncated_file_list_never_proves_no_prior_code(monkeypatch):
    stub(monkeypatch,{'draft':{'parents':['base'],'files':[],'files_may_be_truncated':True}})
    assert plan.anchor('a/b',1)['status']=='commit_files_possibly_truncated'
