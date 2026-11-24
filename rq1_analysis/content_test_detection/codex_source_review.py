"""Replay Codex's direct review of pinned single-file candidates, offline."""
import argparse
import json

import pandas as pd
import portalocker

import ai_assisted as pipeline
from common import HERE, ROOT, file_hash, protect_prior, sha256, write_json
from storage import Store, metadata_request

VERSION = 'codex_source_review_v1'
DEST = pipeline.DEST / VERSION

# Exact anchors on inspected source. A negative requires a whole-file review.
# A positive needs implemented test registration/entry and checking behavior.
REVIEW = {
    ('tencentcloudstack/terraform-provider-tencentcloud',3642): (
        0,'Two-line release note records an infrastructure feature change.',
        ((1,'release-note:enhancement'),(2,'add `priority_scale_in_unhealthy`'))),
    ('litara-app/litara',25): (
        0,'Migration defines the annotation enum and adds a typed, defaulted column.',
        ((2,'CREATE TYPE "AnnotationType" AS ENUM'),(5,'ALTER TABLE "Annotation" ADD COLUMN'))),
    ('jlawyerorg/j-lawyer-org',3311): (
        0,'Migration adds an expiry column and sets the database version.',
        ((1,'ADD COLUMN client_secret_expiry'),(3,'ON DUPLICATE KEY UPDATE settingValue'))),
    ('Splode/pomotroid',396): (
        0,'JSON specifies formatter options, a Svelte plugin and a parser override.',
        ((8,'prettier-plugin-svelte'),(13,'"parser": "svelte"'))),
    ('smart-mcp-proxy/mcpproxy-go',197): (
        0,'Launcher stages existing documentation by replacing and copying the docs directory.',
        ((9,'rm -rf docs'),(12,'cp -r ../docs ./docs'))),
    ('jlawyerorg/j-lawyer-org',3300): (
        0,'Migration adds tag-value columns and writes the release version.',
        ((1,'ALTER TABLE case_tags ADD COLUMN tag_value'),(5,'ON DUPLICATE KEY UPDATE settingValue'))),
    ('roblibob/minute',18): (
        0,'File consists of constants and Notification.Name identifiers for production events.',
        ((3,'public enum MicActivityNotification'),(9,'public extension Notification.Name'))),
    ('baizhiheizi/quill',1822): (
        1,'A test-helper-backed integration case performs a request and checks status and rendered content.',
        ((3,'require "test_helper"'),(6,'test "show renders the public profile"'),(11,'assert_response :success'),
         (12,'assert_match user.name, response.body'))),
    ('litara-app/litara',53): (
        0,'Transaction migrates bookmark records into annotations and drops the superseded table.',
        ((9,'INSERT INTO "Annotation"'),(23,'DROP TABLE "AudiobookBookmark"'),(25,'COMMIT;'))),
    ('litara-app/litara',60): (
        0,'Migration creates the SeriesSlot schema and adds unique and foreign-key constraints.',
        ((2,'CREATE TABLE "SeriesSlot"'),(18,'CREATE UNIQUE INDEX'),(21,'ADD CONSTRAINT'))),
    ('bug-ops/zeph',5383): (
        0,'Four DDL statements add nullable session-setting columns.',
        ((6,'ADD COLUMN IF NOT EXISTS current_model'),(9,'ADD COLUMN IF NOT EXISTS auto_approve_level'))),
    ('baizhiheizi/quill',1582): (
        0,'ActiveRecord migration drops a table and defines its reversible schema and indexes.',
        ((3,'ActiveRecord::Migration'),(5,'drop_table :arweave_transactions'),(9,'create_table :arweave_transactions'))),
    ('strelov1/freehire',348): (
        0,'The only operative statement drops an obsolete column.',
        ((12,'ALTER TABLE jobs'),(13,'DROP COLUMN IF EXISTS remote_unspecified'))),
    ('rustyrazorblade/easy-db-lab',689): (
        0,'Fluent Bit callback filters and maps log fields and returns the transformed record.',
        ((17,'function process(tag, timestamp, record)'),(23,'SEVERITY[p] or "INFO"'),(28,'return 1, timestamp, new'))),
    ('TencentBlueKing/bk-hcm',1956): (
        0,'Migration adds and initializes a production application operation column.',
        ((22,'ADD COLUMN `operation`'),(24,'UPDATE application SET operation = type'),(26,'COMMIT;'))),
    ('hugr-lab/mssql-extension',12): (
        0,'Header defines scalar-function bind data with copy/equality overrides and a registration declaration.',
        ((13,'struct MSSQLRefreshCacheBindData'),(22,'bool Equals'),(34,'void RegisterMSSQLRefreshCacheFunction'))),
    ('S2thend/cursor-history',7): (
        0,'SQLite adapter prepares, executes and closes statements and opens or backs up production databases.',
        ((39,'class BetterSqlite3Database'),(47,'this.nativeDb.prepare'),(81,'open(path:'),(90,'async backup('))),
    ('epam/ai-dial-admin-frontend',3534): (
        1,'Vitest registers a React rendering case and checks the value and absence of a tooltip.',
        ((4,"from 'vitest'"),(34,"test('renders the value as-is"),(40,"expect(screen.getByText('My Project')).toBeInTheDocument()"))),
    ('alotau/dwsolver',28): (
        1,'Standalone test intentionally presents a violation and returns failure if the checker misses it.',
        ((68,'[ "$has_cert_finding" -eq 1 ]'),(72,'did NOT detect the synthetic'),(76,'exit 1'))),
    ('Kulitorum/Decenza',1445): (
        1,'QtTest main discovers a test slot that invokes the provider helper with comparisons.',
        ((53,'QCOMPARE(p.modelName(), expected.first().first)'),(79,'private slots:'),
         (83,'checkProvider<OpenAIProvider>'),(108,'QTEST_GUILESS_MAIN(tst_AIProviders)'))),
    ('qixing-jk/all-api-hub',666): (
        1,'Vitest case checks that implicit account token creation is blocked.',
        ((1,'from "vitest"'),(88,'it("blocks implicit'),(99,'expect(createApiTokenMock).not.toHaveBeenCalled()'))),
    ('b0x42/prizm',23): (
        1,'XCTest test method calls lockVault and checks the authentication and vault repositories.',
        ((6,'RootViewModelLockTests: XCTestCase'),(68,'func testLockVault_callsLockAndClear()'),
         (74,'XCTAssertEqual(mockAuth.lockVaultCalledCount, 1)'))),
    ('TencentBlueKing/bk-ci',12715): (
        1,'JUnit-annotated case runs the version processor and verifies a MockK interaction.',
        ((22,'import org.junit.jupiter.api.Test'),(44,'@Test'),(53,'postProcessInTransactionBeforeVersionCreate'),
         (57,'verify(exactly = 1)'))),
    ('qixing-jk/all-api-hub',596): (
        1,'Vitest onboarding UI case asserts persisted language and the immediate update.',
        ((6,'from "vitest"'),(162,'it("renders the onboarding selector'),(197,'expect(persistedLanguage).toBe("zh_CN")'))),
    ('Soju06/codex-lb',1060): (
        1,'Vitest chart case triggers interactions and checks the active state of the legend row.',
        ((4,'from "vitest"'),(53,'it("highlights the matching legend row'),(69,'expect(legendRow).toHaveAttribute("data-active", "true")'))),
    ('elastic/terraform-provider-elasticstack',2301): (
        1,'Go Test function runs table-driven subtests against JSON request discriminators.',
        ((25,'"testing"'),(260,'func TestSyntheticsMonitorRequestMarshalTypeDiscriminator'),
         (274,'t.Run(tc.name'),(281,'assert.Equal(t, tc.wantType'))),
    ('complytime/complyctl',509): (
        1,'Shell entry point runs integration scenarios, checks output and returns nonzero on recorded failures.',
        ((212,'run_complyctl get'),(219,'assert_contains "get: sync completed"'),(298,'test_get'),(312,'exit 1'))),
    ('alkem-io/client-web',9939): (
        1,'Vitest renders a paginated Spaces component and checks the initial card count and control.',
        ((3,"from 'vitest'"),(69,"test('renders only the first batch"),(71,'expect(countCards()).toBe(12)'))),
    ('unoplatform/uno',22881): (
        1,'Attributed test rebinds an IDE channel and checks connection state before and after connecting.',
        ((10,'[TestClass]'),(13,'[TestMethod]'),(29,'server.WaitForReady()).Should().BeTrue()'))),
    ('unoplatform/uno',23486): (
        1,'Attributed test registers a tool and checks that the tool is in the registry snapshot.',
        ((12,'[TestClass]'),(29,'[TestMethod]'),(38,'tools.Should().ContainSingle()'))),
    ('alonf/specrew',1952): (
        1,'Top-level PowerShell test checks generated amendment artifacts and fails on a broken assertion.',
        ((18,'function Assert-True'),(26,'exit 1'),(282,'Assert-Match -Text $fixtureIndex'),(290,'Assert-True -Condition'))),
    ('alonf/specrew',386): (
        1,'PowerShell harness updates a fixture and fails if unrelated frontmatter is discarded.',
        ((156,'Update-BaselineCommitHashInFrontmatter'),(158,'$updatedPrompt -notmatch'),(162,'exit 1'))),
    ('alonf/specrew',985): (
        1,'PowerShell integration harness invokes the validator and fails if expected diagnostics are missing.',
        ((207,'-File $validatorScript'),(224,'-not (Assert-Match'),(226,'exit 1'))),
    ('alonf/specrew',1889): (
        1,'PowerShell integration harness reruns deployment, asserts idempotency and returns failure on any assertion.',
        ((310,'& $deployScript'),(313,'Assert-True'),(334,'$script:Failures.Count -gt 0'),(337,'exit 1'))),
    ('alonf/specrew',1436): (
        1,'Standalone PowerShell harness checks the generated prompt contract with a terminating assertion.',
        ((8,'exit 1'),(11,'if (-not $Condition)'),(157,'Assert-True ($startScript.Contains'))),
}


def exact_evidence(text, anchors, *, single_line_negative=False):
    lines = text.splitlines()
    complete_one_line = (single_line_negative and len(lines)==1 and bool(lines[0].strip())
                         and list(map(tuple,anchors))==[(1,lines[0])])
    if len({number for number, _ in anchors}) < 2 and not complete_one_line:
        raise ValueError('Review needs at least two distinct source references')
    evidence = []
    for number,symbol in anchors:
        if not 1 <= number <= len(lines) or symbol not in lines[number-1]:
            raise ValueError(f'AI review anchor missing on source line {number}')
        evidence.append({'line':number,'symbol':symbol})
    return evidence


def reviewed_value(item,text,previous):
    if pipeline.review.source(item)!=text:
        raise ValueError('Reviewed source differs from pinned bytes')
    category = item['classification']
    old = previous['classification']
    if old!='uncertain' and (old=='automated_test')!=(category=='automated_test'):
        raise ValueError('Direct AI source review conflicts with existing source analysis')
    evidence = exact_evidence(text,item['anchors'],single_line_negative=category=='not_test')
    value = {'classification':category,'has_executable_tests':category=='automated_test',
             'needs_review':False,'method':'Codex direct AI source review','reason':item['reason'],
             'evidence':evidence,'full_content_examined':category=='not_test'}
    directory = pipeline.DEST / item.get('review_version',VERSION) / 'proofs'
    identity = f"{item['repo_name']}|{item['pr_number']}|{item['content_sha256']}"
    if item.get('review_version') == 'codex_source_review_v16':
        identity += f"|{item['file_path']}"
    target = directory/(sha256(identity.encode())+'.json')
    write_json(target,{**item,**value,'human_reviewed':False,'grok_used':False},immutable=True)
    return {**value,'evidence_reference':target.relative_to(ROOT).as_posix()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round',type=int,choices=range(1,17),default=1)
    args = parser.parse_args()
    plan = REVIEW
    multi = {}
    multi_files = {}
    version = VERSION
    if args.round==2:
        from codex_source_review_round2 import SINGLE, MULTI
        plan,multi = SINGLE,MULTI
        version = 'codex_source_review_v2'
    elif args.round==3:
        from codex_source_review_round2 import MULTI_THIRD
        plan,multi = {},MULTI_THIRD
        version = 'codex_source_review_v3'
    elif args.round==4:
        from codex_source_review_round4 import SINGLE, MULTI
        plan,multi = SINGLE,MULTI
        version = 'codex_source_review_v4'
    elif args.round==5:
        from codex_source_review_round4 import SINGLE_FIFTH, MULTI_FIFTH
        plan,multi = SINGLE_FIFTH,MULTI_FIFTH
        version = 'codex_source_review_v5'
    elif args.round==6:
        from codex_source_review_round6 import SINGLE, MULTI, NEGATIVE_FILES
        plan,multi,multi_files = SINGLE,MULTI,NEGATIVE_FILES
        version = 'codex_source_review_v6'
    elif args.round==7:
        from codex_source_review_round6 import MULTI_SEVENTH
        plan,multi = {},MULTI_SEVENTH
        version = 'codex_source_review_v7'
    elif args.round==8:
        from codex_source_review_round8 import SINGLE, NEGATIVE_FILES
        plan,multi_files = SINGLE,NEGATIVE_FILES
        version = 'codex_source_review_v8'
    elif args.round==9:
        from codex_source_review_round9 import MULTI, NEGATIVE_FILES
        plan,multi,multi_files = {},MULTI,NEGATIVE_FILES
        version = 'codex_source_review_v9'
    elif args.round==10:
        from codex_source_review_round10 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v10'
    elif args.round==11:
        from codex_source_review_round11 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v11'
    elif args.round==12:
        from codex_source_review_round12 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v12'
    elif args.round==13:
        from codex_source_review_round13 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v13'
    elif args.round==14:
        from codex_source_review_round14 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v14'
    elif args.round==15:
        from codex_source_review_round15 import NEGATIVE_FILES
        plan,multi_files = {},NEGATIVE_FILES
        version = 'codex_source_review_v15'
    elif args.round==16:
        from codex_source_review_round16 import MULTI, NEGATIVE_FILES
        plan,multi,multi_files = {},MULTI,NEGATIVE_FILES
        version = 'codex_source_review_v16'
    selected = {(*key,path):(1,reason,anchors)
                for key,(path,reason,anchors) in multi.items()}
    selected.update(multi_files)
    destination = pipeline.DEST/version
    protect_prior()
    pipeline.setup()
    (destination/'proofs').mkdir(parents=True,exist_ok=True)
    candidates = pipeline.review.REPORT/'one_decision_candidates.csv'
    data = pd.read_csv(candidates)
    items = {}
    store = Store()
    extra_rows = []
    for repo,number,path in selected:
        latest = store.data(metadata_request(repo,number))
        files,complete,_,_ = store.files(repo,number)
        if not latest or not complete:
            raise ValueError('Direct review requires a complete pinned PR diff')
        candidate = next(file for file in files if file['filename']==path and file['status']=='added')
        source,provenance,_ = store.content(repo,latest['head_sha'],path,candidate['sha'])
        if source is None:
            raise ValueError('Direct review file is unavailable')
        extra_rows.append({**provenance,'pr_number':number})
    for row in data.to_dict('records')+extra_rows:
        key = row['repo_name'],row['pr_number']
        if key in plan:
            label,reason,anchors = plan[key]
        elif (*key,row['file_path']) in selected:
            label,reason,anchors = selected[(*key,row['file_path'])]
        else:
            continue
        item = {**row,'classification':'automated_test' if label else 'not_test',
                'reason':reason,'anchors':anchors}
        if args.round!=1:
            item['review_version'] = version
        try:
            exact_evidence(pipeline.review.source(item),anchors,single_line_negative=label==0)
        except ValueError as error:
            raise ValueError(f'Direct source review failed for {key}: {error}') from error
        items[(*pipeline.review.identity(row),row['content_sha256'])] = item
    if ({key[:2] for key in items}!=set(plan)|{key[:2] for key in selected}
            or not set(selected).issubset({key[:3] for key in items})):
        raise ValueError('Reviewed candidates differ from the pinned frontier')
    write_json(destination/'manifest.json',{'version':version,'candidate_list_sha256':file_hash(candidates),
               'reference_kind':'Codex direct AI source review','human_reviewed':False,'grok_used':False,
               'items':list(items.values())},immutable=True)
    completed = destination/'latest_run.json'
    if completed.exists():
        pipeline.published_delta()
        print(json.dumps(json.loads(completed.read_bytes()),indent=2))
        return
    pipeline.process(source_reviews=items,review_report=destination)


if __name__=='__main__':
    with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):
        main()
