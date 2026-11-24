"""Versioned offline replay. Never dispatches GitHub or model requests."""
import json
import pandas as pd

import full_cohort
import grok
import scale100
from audit_batch6_quality import classify_frontier
from common import BASE, CACHE, KEY, OUT, file_hash, protect_prior, sha256, write_json
from detector import eligible
from final_static import VERSION, classify_addition
from github_http import read_count
from pipeline import static_prediction
from progress_audit import audit_pending
from storage import Store, git_blob_sha, metadata_request

REPORT = OUT/'full_cohort'/'final_verification_v1'
RECOVERIES = {
    '7df1a7352bab1f31e852db0a46170626a3a4a50eeb0a399f6a97410c0cec5e71': (
        '1279776f61f99392b592c9c428db59372e728ac505850aab06fb1d66489c5c49',
        'tests/test_status_cli.rs', {21:'#[test]',22:'#[cfg(unix)]',
        23:'fn test_status_human_output_shows_recognized_skills_mode_hint()',50:'assert!('}),
    '95f91517d14bc62db67902f9496713459316e3c704b3cb448c8b82c602c5c42f': (
        'e9753557ab17e2c3e16c8d73b02ce8994b6198e2f14ed1761e83c63550cae0f0',
        'MeshtasticTests/NodeBackupManagerTests.swift', {8:'import Testing',
        74:'@Test("createBackup creates file copy and updates index")',
        76:'func testCreateBackupSuccess() async throws {',94:'#expect(entry.nodeNum == 12345)'})
}


class OfflineResolver(scale100.Resolver):
    def __init__(self):
        super().__init__(dry_run=True)
        self.accepted={}
        self.rejected={}
        for folder in [CACHE/'offline_revalidated',CACHE/'repair_smoke/grok',CACHE/'grok']:
            for path in sorted(folder.glob('*.json')):
                record=json.loads(path.read_bytes())
                if record.get('status')=='validated':
                    self.accepted.setdefault(record['content_sha256'],(path,record))
                if record.get('status')=='provider_or_validation_failure':
                    self.rejected.setdefault(record['content_sha256'],record)

    def recover(self,text,path,digest):
        key,expected_path,anchors=RECOVERIES[digest]
        if path!=expected_path:
            return None
        content=(OUT/'content'/f'{digest}.txt').read_bytes()
        if sha256(content)!=digest or content.decode('utf-8-sig')!=text:
            raise ValueError('Recovered source identity mismatch')
        lines=text.splitlines()
        assert all(1<=n<=len(lines) and token in lines[n-1] for n,token in anchors.items())
        path_to_cache=CACHE/'grok'/f'{key}.json'
        record=json.loads(path_to_cache.read_bytes())
        diag=record['diagnostic']
        safe,_=grok.sanitize(text)
        assert record['content_sha256']==digest and diag['complete_input']
        assert diag['finish_reason']=='REASON_STOP' and sha256(safe.encode())==diag['sanitized_input_sha256']
        parsed=grok.validate_output(diag['raw_output'],safe)
        assert parsed==grok.validate_output(diag['raw_output'],text)
        assert parsed.classification=='automated_test' and not parsed.needs_review
        # Older responses have verbatim excerpts, whose exact-source validation
        # is complemented here by independently located framework/test anchors.
        value={**record,**parsed.model_dump(),'status':'validated','complete_input':True,
               'offline_revalidation':{'original_cache_key':key,'source_anchors':anchors}}
        grok.validate_cached_classification(value,text)
        folder=REPORT/'recovered_responses'
        folder.mkdir(exist_ok=True)
        evidence=folder/f'{key}.json'
        write_json(evidence,value,immutable=True)
        return evidence,value

    def resolve(self,text,path,lang,raw_hash,strong=None):
        cached=self.accepted.get(raw_hash)
        if not cached and raw_hash in RECOVERIES:
            cached=self.recover(text,path,raw_hash)
        if cached:
            proof,record=cached
            assert record['content_sha256']==raw_hash and record['model']==grok.MODEL
            assert record['reasoning_effort']==grok.REASONING
            grok.validate_cached_classification(record,text)
            return {**record,'cache_hit':True,'classification_cache_reference':proof.relative_to(BASE.parent).as_posix()}
        if raw_hash in self.rejected:
            return {**self.rejected[raw_hash],'cache_hit':True}
        return grok.GrokResolver.resolve(self,text,path,lang,raw_hash,strong)

    def static_classifier(self, text, path, digest):
        cached = static_prediction(text,path,digest)
        if cached['classification']!='uncertain':
            return cached
        proof = classify_addition(text,path)
        if not proof:
            return cached
        lines = text.splitlines()
        if any(not 1 <= e['line'] <= len(lines) or e['symbol'] not in lines[e['line']-1]
               for e in proof['evidence']):
            return cached
        key = sha256(f'{VERSION}|{path}|{digest}'.encode())
        location = REPORT/'file_proofs'/f'{key}.json'
        location.parent.mkdir(exist_ok=True)
        proof.update(content_sha256=digest,file_path=path,
                     evidence_reference=location.relative_to(BASE.parent).as_posix())
        write_json(location,proof,immutable=True)
        return proof


def verify_pr(row, evidence, store, groups):
    key=(row['repo_name'],int(row['pr_number']))
    files,complete,_,_=store.files(*key)
    head=store.data(metadata_request(*key))['head_sha']
    assert complete and head==row['pinned_commit_sha']
    expected={(f.file_path,f.change_status) for f in groups[key].itertuples()}
    assert expected=={(item['filename'],item['status']) for item in files}
    candidates={f['filename']:f for f in files if f['status']=='added' and eligible(f['filename'])}
    audits=evidence[(evidence.repo_name==key[0]) & (evidence.pr_number==key[1])].set_index('file_path')
    if row['test_added_content_verified']==1:
        selected=[row['confirmed_file_path']]
        assert audits.loc[selected[0],'classification']=='automated_test'
        assert row['file_content_hash']==audits.loc[selected[0],'content_sha256']
    else:
        selected=list(candidates)
        assert row['inspection_complete'] and set(audits.index)==set(candidates)
        assert audits.classification.isin(['not_test','test_support']).all()
    for path in selected:
        audit=audits.loc[path]
        assert audit.examined and audit.commit_sha==head
        raw=(OUT/'content'/f'{audit.content_sha256}.txt').read_bytes()
        assert sha256(raw)==audit.content_sha256 and git_blob_sha(raw)==candidates[path]['sha']


def main():
    root=full_cohort.DEST
    from cohort_overlay import installed
    if installed(root):
        from cohort_overlay import read_delta
        delta = read_delta(root)
        evidence = pd.read_csv(REPORT/'verified_delta_evidence.csv')
        store, groups = Store(), full_cohort.groups()
        for row in delta.to_dict('records'):
            verify_pr(row,evidence,store,groups)
        protect_prior()
        print((REPORT/'summary.json').read_text(encoding='utf-8'))
        return
    REPORT.mkdir(exist_ok=True)
    main_path=root/'current_main_outcomes.csv'
    ledger=OUT/'api_ledger.json'
    original=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet',columns=KEY)
    protected={p:file_hash(p) for p in [main_path,ledger,*root.glob('batch_*/sample.csv'),
                                        *root.glob('circuit_state_*.json'),
                                        *root.glob('evidence_v5_trial/*.json'),
                                        *root.glob('evidence_v5_trial/grok/*.json')]}
    write_json(REPORT/'input_hashes.json',{str(p.relative_to(OUT)):h for p,h in protected.items()},
               immutable=True)
    github_before=read_count(CACHE)
    main=pd.read_csv(main_path)
    assert len(main)==3186 and not main.duplicated(KEY).any()
    assert set(main[KEY].itertuples(index=False,name=None))==set(original.itertuples(index=False,name=None))
    label='test_added_content_verified'
    unknown=main.loc[main[label].isna()].copy()
    groups=full_cohort.groups()
    resolver=OfflineResolver()
    states=audit_pending(unknown,main,groups,resolver)
    ready=states.loc[states.verification_state.eq('cache_ready_for_replay'),KEY]
    delta_source=unknown.merge(ready,on=KEY,validate='one_to_one')
    scale100.DEST=REPORT/'replay'
    (scale100.DEST/'checkpoints').mkdir(parents=True,exist_ok=True)
    delta,evidence,pending=scale100.run_rows(delta_source,resolver,fetch=False,groups=groups)
    assert not pending and len(delta)==len(ready) and delta[label].notna().all()
    store=Store()
    for row in delta.to_dict('records'):
        verify_pr(row,evidence,store,groups)
    combined=main.set_index(KEY).copy()
    for row in delta.to_dict('records'):
        key=tuple(row[k] for k in KEY)
        assert pd.isna(combined.loc[key,label])
        for col in combined.columns:
            if col in row:
                combined.loc[key,col]=row[col]
    combined=combined.reset_index()
    pd.testing.assert_frame_equal(main.loc[main[label].notna()].set_index(KEY),
                                  combined.loc[main[label].notna()].set_index(KEY),
                                  check_dtype=False)
    frontier=states.loc[~states.verification_state.eq('cache_ready_for_replay')].copy()
    frontier[['next_step','uncached_model_files','other_unresolved_items']]=pd.DataFrame(
        [classify_frontier(row) for row in frontier.itertuples()],index=frontier.index)
    rank={'model_only':0,'github_reconciliation':1,'github_acquisition':1,
          'mixed_manual_and_model':2,'manual_or_unavailable':3}
    frontier['priority']=frontier.next_step.map(rank)
    frontier=frontier.sort_values(['priority','uncached_model_files',*KEY])
    reconciliation=[]
    for row in frontier[frontier.next_step.eq('github_reconciliation')].itertuples():
        key=(row.repo_name,row.pr_number)
        files,complete,_,reason=store.files(*key)
        meta=store.data(metadata_request(*key))
        metadata_record=store.record(metadata_request(*key))
        frozen={(f.file_path,f.change_status) for f in groups[key].itertuples()}
        observed={(f['filename'],f['status']) for f in files or []}
        reconciliation.append(dict(zip(KEY,key), reason=reason, head=meta.get('head_sha') if meta else None,
                                   metadata_error=metadata_record.get('error') if metadata_record else None,
                                   frozen_only=sorted(frozen-observed) if complete else None,
                                   observed_only=sorted(observed-frozen) if complete else None))
    assert read_count(CACHE)==github_before and all(file_hash(p)==h for p,h in protected.items())
    frozen_count=protect_prior()
    delta.to_csv(REPORT/'verified_delta.csv',index=False)
    evidence.to_csv(REPORT/'verified_delta_evidence.csv',index=False)
    frontier.to_csv(REPORT/'unknown_frontier.csv',index=False)
    write_json(REPORT/'github_reconciliation.json',reconciliation)
    combined.to_csv(REPORT/'verified_cohort.csv',index=False)
    summary={'before_unknown':len(unknown),'new_positive':int(delta[label].eq(1).sum()),
             'new_negative':int(delta[label].eq(0).sum()),
             'positive':int(combined[label].eq(1).sum()),'negative':int(combined[label].eq(0).sum()),
             'unknown':int(combined[label].isna().sum()),'next_steps':frontier.next_step.value_counts().to_dict(),
             'one_model_file_only':int((frontier.next_step.eq('model_only') & frontier.uncached_model_files.eq(1)).sum()),
             'github_used':github_before,'frozen_files_verified':frozen_count,'new_api_requests':0}
    write_json(REPORT/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
