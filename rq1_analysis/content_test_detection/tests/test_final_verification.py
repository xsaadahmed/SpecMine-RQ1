import pytest

from evidence_trial import CASES, source_for
from final_reference_gate import declaration_choices, response_schema, verify_anchor
from final_static import android_launcher, classify_addition, schema_only, settings_only, swift_test
import final_verify


@pytest.mark.parametrize('case', CASES)
def test_original_trial_fixtures_can_be_resolved_from_full_source(case):
    source, _ = source_for(case)
    assert classify_addition(source,case[2])['classification']==case[4]


def test_candidate_role_comes_from_the_actual_parsed_declaration():
    source, _ = source_for(CASES[0])
    digest=CASES[0][3]
    choices=declaration_choices(source,'svelte',digest)
    assert list(choices.values())==[{'line':27,'symbol':'formatAmount','role':'declaration'}]
    key=next(iter(choices))
    assert response_schema(choices)['properties']['reference_id']['enum']==[key,None]
    assert verify_anchor({'judgment':'not_test','reference_id':key},choices,source,digest,'svelte')['line']==27
    for bad in ({'judgment':'not_test','reference_id':'$props'},
                {'judgment':'not_test','reference_id':key,'role':'assertion'}):
        with pytest.raises(ValueError):
            verify_anchor(bad,choices,source,digest,'svelte')
    with pytest.raises(ValueError):
        verify_anchor({'judgment':'not_test','reference_id':key},choices,'\n'+source,digest,'svelte')


def test_markup_and_launcher_rules_decline_active_behavior():
    source, _=source_for(CASES[0])
    assert classify_addition(source.replace('</script>', 'test("case", () => expect(1).toBe(1));</script>'),
                             CASES[0][2]) is None
    assert classify_addition(source+'\n<slot />',CASES[0][2]) is None
    source,_=source_for(CASES[1])
    assert android_launcher(source)
    assert not android_launcher(source+'\nDescribe "a test" {}')
    assert not android_launcher(source.replace('java -version','Write-Host "$(Invoke-Expression $payload)"'))


def test_sql_and_configuration_require_complete_supported_grammar():
    assert schema_only('ALTER TABLE "Shelf" ADD COLUMN "logic" TEXT NOT NULL DEFAULT \'AND\';')
    for candidate in ["DO $$ BEGIN RAISE EXCEPTION 'check'; END $$;",
                      "ALTER TABLE t ADD COLUMN i INTEGER DEFAULT test();",
                      "ALTER TABLE t DROP COLUMN a; /*! SELECT assert_true(0); */",
                      "ALTER TABLE t DROP COLUMN a"]:
        assert not schema_only(candidate)
    mini='[submodule "lib"]\npath = lib\nurl = https://example.invalid/lib\n'
    assert settings_only(mini,'.gitmodules')
    assert not settings_only(mini+'update = !test_command\n','.gitmodules')
    assert not settings_only('{"plugins":["module.js"]}', '.prettierrc')


def test_swift_requires_implemented_assertion_in_a_real_discoverable_test():
    registered='import XCTest\nclass Example: XCTestCase {\nfunc testExample() {\nXCTAssertTrue(true)\n}\n}'
    assert swift_test(registered)['classification']=='automated_test'
    assert swift_test(registered.replace('XCTAssertTrue(true)','// XCTAssertTrue(true)')) is None
    assert swift_test(registered.replace('func testExample()','func helper()')) is None
    assert swift_test('#if NEVER\n'+registered+'\n#endif') is None
    assert swift_test(registered.replace('XCTAssertTrue(true)','throw XCTSkip()')) is None


@pytest.mark.parametrize('case',[
    ('dallay/agentsync',344,'tests/test_status_cli.rs',
     '7df1a7352bab1f31e852db0a46170626a3a4a50eeb0a399f6a97410c0cec5e71','automated_test'),
    ('meshtastic/Meshtastic-Apple',1871,'MeshtasticTests/NodeBackupManagerTests.swift',
     '95f91517d14bc62db67902f9496713459316e3c704b3cb448c8b82c602c5c42f','automated_test'),
])
def test_archived_role_proofs_recover_verbatim_citation_failures(case,tmp_path,monkeypatch):
    monkeypatch.setattr(final_verify,'REPORT',tmp_path)
    source,_=source_for(case)
    proof,value=final_verify.OfflineResolver().recover(source,case[2],case[3])
    assert proof.exists() and value['classification']=='automated_test'
    with pytest.raises(ValueError,match='identity mismatch'):
        final_verify.OfflineResolver().recover(source+'\n',case[2],case[3])
