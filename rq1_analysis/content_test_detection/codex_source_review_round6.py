"""Pinned source judgments for the sixth offline review round."""

SINGLE = {
    ('travishathaway/osmprj',10): (0,'Installer fetches and invokes a platform installer and updates shell configuration.',
        ((104,'--output "$INSTALLER_SCRIPT"'),(149,'"$INSTALLER_SCRIPT" --output-directory'),(180,'update_shell "$HOME/.bashrc"'))),
    ('smart-mcp-proxy/mcpproxy-go',183): (0,'Release utility collects commit messages and generates release notes with a fallback.',
        ((246,'local commits'),(247,'collect_commits'),(260,'call_claude_api "$prompt"'),(266,'generate_fallback'))),
    ('jdjingdian/StaticRouteHelper',4): (0,'Production Swift component serializes route requests and writes them to the system routing socket.',
        ((25,'static func write(request:'),(33,'socket(PF_ROUTE'),(166,'Darwin.write(sock,'))),
}

MULTI = {
    ('Kulitorum/Decenza',1412): ('tests/tst_livesteamcoach.cpp',
        'QtTest registers a slot that starts a steam fixture and checks that disabled coaching emits no cues.',
        ((93,'private slots:'),(118,'void bothOff_noCuesNoSpeech'),(124,'QCOMPARE(fx.cueSpy.count(), 0)'),(409,'QTEST_GUILESS_MAIN'))),
    ('alotau/dwsolver',21): ('tests/test_lib_api.c',
        'Standalone C runner exercises the API and checks documented defaults with a terminating assertion.',
        ((54,'exit(1)'),(80,'opts.rounding_flag'),(248,'int main(void)'),(252,'test_1_defaults();'))),
    ('hugr-lab/mssql-extension',163): ('test/cpp/test_gssapi_runtime.cpp',
        'Standalone main checks the runtime loader contract and returns failure for assertion failures.',
        ((33,'++g_failures'),(51,'Check(Contains(msg'),(81,'TestUnavailableMessageContract();'),(88,'return 1;'))),
    ('hugr-lab/mssql-extension',49): ('test/cpp/test_fedauth_encoding.cpp',
        'Standalone test checks encoded size and byte values, using a failing assertion macro.',
        ((36,'assert(false)'),(69,'ASSERT_EQ(encoded.size()'),(463,'test_is_azure_endpoint_azure_sql();'),(480,'test_login7_no_fedauth_extension_with_sql_auth();'))),
    ('hugr-lab/mssql-extension',102): ('test/cpp/test_login7_encoding.cpp',
        'C++ runner executes fixture and encoding-equivalence checks and returns nonzero on errors.',
        ((115,'#define CHECK_EQ'),(437,'int main()'),(443,'TestBuildLogin7FixtureMatrix();'),(461,'return 1;'))),
    ('hugr-lab/mssql-extension',118): ('test/cpp/test_issue_96_attach_loop.cpp',
        'Standalone integration regression runs repeated database operations and reports a nonzero status on a failed iteration.',
        ((90,'int main()'),(128,'r_query->HasError()'),(145,'failed_iter > 0'),(151,'return 1;'))),
    ('FBakkensen/al-build-tools',39): ('scripts/ci/test-bootstrap-install.ps1',
        'Container-based installation test validates the expected transcript and propagates a failure status.',
        ((1270,'-not (Test-Path $transcriptPath)'),(1273,'$exitCode = 1'),(1275,"$summary['success'] = $false"),(1315,'exit $finalExitCode'))),
    ('ambient-code/platform',1315): ('scripts/test-coderabbit-integration.sh',
        'Integration suite asserts status and JSON values for application endpoints and returns failure when assertions fail.',
        ((112,'assert_status "$STATUS" "401"'),(116,'assert_json "$BODY" "connected" "false"'),(227,'"$FAIL" -gt 0'),(229,'exit 1'))),
    ('alonf/specrew',189): ('tests/integration/distribution-module-init.ps1',
        'Integration harness checks a fixture bootstrap, output paths and an idempotency rerun.',
        ((148,'$firstRun.ExitCode -ne 0'),(182,'$missingPaths.Count -gt 0'),(208,'$secondRun.ExitCode -ne 0'),(210,'exit 1'))),
    ('cardano-foundation/moog',118): ('test/Lib/GitHub/Auth/DeviceFlowSmokeSpec.hs',
        'Hspec case checks the token evidence renderer against an expected length and prefix behavior.',
        ((11,'import Test.Hspec'),(16,'it "prints the token prefix'),(23,'T.length evidence `shouldBe` 13'))),
}

NEGATIVE_FILES = {
    ('Splode/pomotroid',374,'src/lib/components/Tooltip.svelte'):
        (0,'Production tooltip component manages positioning, visibility, and pointer events.',
         ((24,'async function show()'),(45,'function updatePosition()'),(86,'{#if visible}'))),
    ('Splode/pomotroid',374,'src/lib/components/TooltipInfo.svelte'):
        (0,'Production component renders a tooltip icon and prevents its click from propagating.',
         ((11,'<Tooltip {text}'),(20,'e.stopPropagation()'))),
    ('Yourdaylight/stock_datasource',28,'src/stock_datasource/modules/chat/schema.sql'):
        (0,'ClickHouse schema defines chat session and message tables.',
         ((2,'CREATE TABLE IF NOT EXISTS chat_sessions'),(15,'CREATE TABLE IF NOT EXISTS chat_messages'))),
    ('Yourdaylight/stock_datasource',28,'src/stock_datasource/modules/datamanage/schema.sql'):
        (0,'ClickHouse schema defines a sync-history table and its partitioning.',
         ((2,'CREATE TABLE IF NOT EXISTS sync_history'),(17,'PARTITION BY toYYYYMM(started_at)'))),
    ('denisfl/inbox',48,'db/migrate/20260320133004_create_action_text_tables.action_text.rb'):
        (0,'Rails migration creates rich-text storage and an index.',
         ((2,'ActiveRecord::Migration'),(7,'create_table :action_text_rich_texts'),(14,'index_action_text_rich_texts_uniqueness'))),
    ('denisfl/inbox',48,'db/migrate/20260320140000_migrate_markdown_to_action_text.rb'):
        (0,'Rails data migration rewrites existing Markdown and provides a down migration.',
         ((3,'ActiveRecord::Migration'),(19,'ActionText::RichText.create!'),(74,'ActionText::RichText.where'))),
    ('kalbasit/ncps',1330,'migrations/mysql/20260605021047_add_bytes_stored_at_to_nar_files.sql'):
        (0,'MySQL up/down migration adds and removes one nullable timestamp column.',
         ((3,'ADD COLUMN'),(7,'DROP COLUMN'))),
    ('kalbasit/ncps',1330,'migrations/postgres/20260605021047_add_bytes_stored_at_to_nar_files.sql'):
        (0,'PostgreSQL up/down migration adds and removes one nullable timestamp column.',
         ((3,'ADD COLUMN'),(7,'DROP COLUMN'))),
    ('litara-app/litara',32,'apps/api/prisma/migrations/20260404190932_remove_default_library/migration.sql'):
        (0,'Migration makes a library reference nullable and recreates its foreign key.',
         ((5,'DROP NOT NULL'),(8,'ON DELETE SET NULL'))),
    ('litara-app/litara',32,'apps/api/prisma/migrations/20260404224831_cleanup_system_libraries/migration.sql'):
        (0,'Data migration unassigns books, removes system libraries and repairs the key.',
         ((3,'UPDATE "Book" SET "libraryId" = NULL'),(7,'DELETE FROM "Library"'),(12,'ON DELETE SET NULL'))),
    ('jlawyerorg/j-lawyer-org',3290,'j-lawyer-server-entities/src/java/db/migration/V3_5_0_5__AddAssistantPromptModelConfig.sql'):
        (0,'DDL adds prompt configuration columns and writes the schema version.',
         ((1,'ADD COLUMN model_ref'),(4,'ON DUPLICATE KEY UPDATE'))),
    ('jlawyerorg/j-lawyer-org',3290,'j-lawyer-server-entities/src/java/db/migration/V3_5_0_6__AddAssistantPromptSystemPrompt.sql'):
        (0,'DDL adds a prompt column and writes the schema version.',
         ((1,'ADD COLUMN system_prompt'),(3,'ON DUPLICATE KEY UPDATE'))),
    ('jlawyerorg/j-lawyer-org',3290,'j-lawyer-server-entities/src/java/db/migration/V3_5_0_7__ContactsAddTaxDeduction.sql'):
        (0,'DDL adds two contact fields and writes the schema version.',
         ((1,'ALTER TABLE contacts ADD'),(4,'ON DUPLICATE KEY UPDATE'))),
    ('kalbasit/ncps',1108,'db/migrations/mysql/20260318053904_add_pinned_closures_table.sql'):
        (0,'MySQL up/down migration creates and drops a table.',
         ((2,'CREATE TABLE pinned_closures'),(11,'DROP TABLE IF EXISTS pinned_closures'))),
    ('kalbasit/ncps',1108,'db/migrations/postgres/20260318053904_add_pinned_closures_table.sql'):
        (0,'PostgreSQL up/down migration creates and drops a table.',
         ((2,'CREATE TABLE pinned_closures'),(10,'DROP TABLE IF EXISTS pinned_closures'))),
    ('kalbasit/ncps',1108,'db/migrations/sqlite/20260318053903_add_pinned_closures_table.sql'):
        (0,'SQLite up/down migration creates and drops a table.',
         ((2,'CREATE TABLE "pinned_closures"'),(10,'DROP TABLE IF EXISTS "pinned_closures"'))),
}

MULTI_SEVENTH = {
    ('hugr-lab/mssql-extension',51): ('test/cpp/test_jwt_parser.cpp',
        'Standalone executable invokes JWT parser and expiry test cases with terminating checks.',
        ((38,'assert(false)'),(272,'ASSERT_FALSE(IsTokenExpired'),(322,'int main()'),(343,'test_is_token_expired_with_margin();'))),
    ('FBakkensen/al-build-tools',4): ('tests/contract/test_clean_pass.sh',
        'Shell contract test asserts that the clean-repository analyzer succeeds with no blocking findings.',
        ((9,'run-static-analysis.sh'),(14,'$exit_code -ne 0'),(23,'$blocking_count -ne 0'),(27,'exit 1'))),
    ('hugr-lab/mssql-extension',8): ('test/cpp/test_ddl_translator.cpp',
        'Standalone C++ test checks SQL identifier quoting and translates known DDL inputs into expected output.',
        ((32,'assert(false)'),(53,'ASSERT_EQ(MSSQLDDLTranslator::QuoteIdentifier'),(332,'int main()'),(370,'return 1;'))),
    ('hugr-lab/mssql-extension',5): ('test/cpp/test_tls_connection.cpp',
        'Integration executable checks that fixture connections enable TLS and expose the expected connection state.',
        ((85,'assert(false && "TLS authentication should succeed")'),(89,'assert(conn->IsTlsEnabled())'),
         (94,'assert(conn->GetState() == ConnectionState::Idle)'),(547,'int main()'))),
    ('smart-mcp-proxy/mcpproxy-go',394): ('contrib/linux-repos/smoke-test-debian.sh',
        'Debian package smoke test installs the package and compares its reported version with the expected release.',
        ((27,'apt-get -qq install -y mcpproxy'),(28,'mcpproxy --version'),(32,'"${actual}" != "${VERSION}"'),(34,'exit 1'))),
    ('alotau/dwsolver',14): ('tests/test_guidefile.sh',
        'Fixture-based CLI test checks error status and output for invalid guidefiles.',
        ((82,'fixtures/bad_count.guidefile'),(84,'assert_exit "bad_count non-zero exit"'),(89,'-z "$_out"'),(107,'exit 1'))),
    ('hugr-lab/mssql-extension',31): ('test/cpp/test_ctas_type_mapping.cpp',
        'Standalone C++ tests assert expected SQL column definitions and mappings.',
        ((41,'assert(false)'),(282,'ASSERT_CONTAINS(ddl, "[id] INT NOT NULL")'),(322,'int main()'),(358,'return 1;'))),
    ('hugr-lab/mssql-extension',33): ('test/cpp/test_bcp_row_encoder.cpp',
        'Standalone C++ test checks encoded buffer bytes against expected fixtures.',
        ((58,'assert(false)'),(83,'ASSERT_BYTES_EQ(buffer, expected)'),(598,'int main()'),(649,'return 1;'))),
    ('hugr-lab/mssql-extension',4): ('test/cpp/test_connection_pool.cpp',
        'Standalone connection-pool test asserts liveness and exact created, active, and idle connection counts.',
        ((96,'assert(stats.connections_created == 1)'),(97,'assert(stats.active_connections == 1)'),
         (101,'assert(conn1->IsAlive())'),(290,'int main()'))),
    ('hugr-lab/mssql-extension',7): ('test/cpp/test_simple_query.cpp',
        'Standalone database integration executable runs query cases and checks returned strings and rows.',
        ((91,'assert(result == "42")'),(109,'assert(result == "Hello, World!")'),(422,'int main()'),(477,'return 1;'))),
    ('FBakkensen/al-build-tools',8): ('tests/contract/test_bootstrap_install_basic.sh',
        'Standalone installer test executes the fixture and checks status, emitted messages and installed files.',
        ((25,'bash "$WORK/bin/install"'),(31,'exit 1'),(37,'bh_assert_installed "$dest"'),(43,'main "$@"'))),
    ('hugr-lab/mssql-extension',110): ('test/cpp/codec/test_binary_codec.cpp',
        'Standalone runner invokes binary codec cases with value comparisons and exits on recorded failures.',
        ((54,'#define CHECK_EQ'),(59,'++failures'),(264,'int main()'),(265,'TestDecodeNonPLPEmpty();'),(282,'return 1;'))),
}
