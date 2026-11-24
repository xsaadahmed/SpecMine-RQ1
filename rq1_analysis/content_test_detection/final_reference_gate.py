"""Offline evidence-choice prototype. It has no provider transport or paid gate."""
import json

import pandas as pd

import grok
from common import OUT, sha256, write_json
from detector import parser_for, walk
from evidence_trial import CASES, source_for
from final_static import classify_addition
from final_verify import OfflineResolver, REPORT


def declaration_choices(source, language, digest):
    """Find real declaration anchors; existence here does not prove non-test."""
    raw = source.encode()
    if sha256(raw)!=digest:
        raise ValueError('Source hash does not match the reference input')
    origins = [(0, raw)]
    if language in {'svelte', 'vue'}:
        parsed = parser_for(language).parse(raw).root_node
        if parsed.has_error:
            return {}
        origins = [(n.start_byte, raw[n.start_byte:n.end_byte])
                   for n in walk(parsed) if n.type=='raw_text'
                   and n.parent and n.parent.type=='script_element']
        language = 'typescript'
    if language not in {'javascript','typescript','tsx'}:
        return {}
    candidates = {}
    for offset, data in origins:
        root = parser_for(language).parse(data).root_node
        if root.has_error:
            continue
        for node in root.named_children:
            declaration = node.child_by_field_name('declaration') if node.type=='export_statement' else node
            if not declaration or declaration.type not in {'function_declaration','class_declaration'}:
                continue
            name = declaration.child_by_field_name('name')
            if not name:
                continue
            symbol = data[name.start_byte:name.end_byte].decode()
            line = raw.count(b'\n',0,offset+name.start_byte)+1
            ref = {'line':line,'symbol':symbol,'role':'declaration'}
            trial = {'classification':'not_test','has_executable_tests':False,'language':language,
                     'evidence':[ref],'reason':'Check declaration location only','needs_review':False}
            try:
                grok.validate_evidence_v5(trial,source)
            except ValueError:
                continue
            key = sha256(f'{digest}|{line}|{symbol}|declaration'.encode())[:20]
            candidates[key] = ref
    return candidates


def response_schema(catalog):
    return {'type':'object','properties':{
        'judgment':{'enum':['not_test','uncertain']},
        'reference_id':{'enum':list(catalog)+[None]},
    },'required':['judgment','reference_id'],'additionalProperties':False}


def verify_anchor(choice, catalog, source, digest, language):
    # Resolve IDs from a fresh parse, never from a model-provided name or line.
    if set(choice)!={'judgment','reference_id'}:
        raise ValueError('Unexpected response fields')
    if choice=={'judgment':'uncertain','reference_id':None}:
        return None
    if choice['judgment']!='not_test' or not isinstance(choice['reference_id'],str):
        raise ValueError('Unsupported judgment or reference')
    fresh=declaration_choices(source,language,digest)
    key=choice['reference_id']
    if fresh!=catalog or key not in fresh:
        raise ValueError('Reference is outside the current source choices')
    return fresh[key]


def main():
    REPORT.mkdir(exist_ok=True)
    cases=[
        (*CASES[0], 'Presentation-only component with read-only formatting and display'),
        (*CASES[1], 'Launcher sets environment, checks Java version and starts Expo Android'),
        (*CASES[2], 'JUnit Test annotation and AssertJ checks inside registered Kotlin methods'),
        ('alonf/specrew',627,'tests/integration/validator-parallelization.tests.ps1',
         '621b9bd7ac03b1303362ca5acfbdaed734eac2c50b9a1e928bf64f7a12c34c31','automated_test',
         'Standalone comparisons call Write-Fail, whose implementation exits with status 1'),
        ('dallay/agentsync',344,'tests/test_status_cli.rs',
         '7df1a7352bab1f31e852db0a46170626a3a4a50eeb0a399f6a97410c0cec5e71','automated_test',
         'Rust test registered on Unix runs CLI status and asserts success and reported modes'),
        ('meshtastic/Meshtastic-Apple',1871,'MeshtasticTests/NodeBackupManagerTests.swift',
         '95f91517d14bc62db67902f9496713459316e3c704b3cb448c8b82c602c5c42f','automated_test',
         'Swift Testing suite creates a backup and checks its resulting entry'),
    ]
    rows=[]
    for repo,pr,path,digest,expected,notes in cases:
        text,prov=source_for((repo,pr,path,digest,expected))
        result=classify_addition(text,path) or OfflineResolver().static_classifier(text,path,digest)
        if result['classification']=='uncertain' and result.get('language'):
            cached=OfflineResolver().resolve(text,path,result['language'],digest)
            if cached.get('status')=='validated':
                result=cached
        rows.append({'repo_name':repo,'pr_number':pr,'file_path':path,'commit_sha':prov['commit_sha'],
                     'content_sha256':digest,'source_review_expectation':expected,
                     'review_basis':notes,'offline_result':result['classification'],
                     'independent_reviewer_label':'','independent_reviewer_id':''})
    assert all(row['offline_result']==row['source_review_expectation'] for row in rows)
    packet=pd.DataFrame(rows)
    packet.drop(columns=['independent_reviewer_label','independent_reviewer_id']).to_csv(
        REPORT/'source_review_expectations.csv',index=False)
    # Keep the worksheet blind, and never erase a review on a later replay.
    worksheet=REPORT/'blind_review_packet.csv'
    identity_columns=['repo_name','pr_number','file_path','commit_sha','content_sha256']
    if worksheet.exists():
        recorded=pd.read_csv(worksheet)
        if not recorded[identity_columns].equals(packet[identity_columns]):
            raise ValueError('Existing review packet does not match the frozen cases')
    else:
        packet[identity_columns+['independent_reviewer_label','independent_reviewer_id']].to_csv(
            worksheet,index=False)
    source,_=source_for(CASES[0])
    digest=CASES[0][3]
    catalog=declaration_choices(source,'svelte',digest)
    assert len(catalog)==1 and next(iter(catalog.values()))['symbol']=='formatAmount'
    assert verify_anchor({'judgment':'not_test','reference_id':next(iter(catalog))},
                         catalog,source,digest,'svelte')==next(iter(catalog.values()))
    write_json(REPORT/'reference_gate.json',{'offline_fixture_matches':len(rows),
               'human_reviewed':0,'paid_approved':False,
               'model_false_positives':None,'model_false_negatives':None,
               'model_unsupported_citations':None,'model_abstentions':None,
               'source_sha256':digest,'choices':catalog,'response_schema':response_schema(catalog),
               'limitation':'Anchors prove location and role only. No independent labels or live semantic validation.'})
    print(json.dumps({'offline_fixture_matches':len(rows),'paid_approved':False},indent=2))


if __name__ == '__main__':
    main()
