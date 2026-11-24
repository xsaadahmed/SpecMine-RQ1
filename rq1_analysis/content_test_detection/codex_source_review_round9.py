"""Direct review of Ruby RSpec suites, production code and tooling."""

MULTI = {
    ('denisfl/inbox',60): ('spec/helpers/wiki_link_renderer_spec.rb',
        'RSpec examples call the wiki-link renderer and check rendered links and broken-link markup.',
        ((3,'RSpec.describe ApplicationHelper'),(8,'it "replaces [[Title]]'),(12,'expect(result).to include'),
         (31,'expect(result).to include'))),
    ('denisfl/inbox',64): ('spec/jobs/storage_health_check_job_spec.rb',
        'RSpec examples invoke the storage health job with stubbed adapters and assert persisted statuses.',
        ((3,'RSpec.describe StorageHealthCheckJob'),(14,'it "updates status to ok'),(22,'described_class.perform_now'),
         (25,'expect(setting.status).to eq("ok")'))),
}

NEGATIVE_FILES = {
    ('alkem-io/server',5970,'.scripts/gql-request-interactive.sh'):
        (0,'Interactive client reads a user-supplied query and prints the response without checking an expected result.',
         ((37,'QUERY=$(cat'),(47,'RESPONSE=$(gql_request_interactive'),(48,'jq .'))),
    ('alkem-io/server',5970,'.scripts/interactive-login.sh'):
        (0,'Interactive login utility prepares and saves a session for later requests.',
         ((34,'mkdir -p'),(44,'kratos_login_browser'),(49,'chmod 600'))),
    ('hugr-lab/mssql-extension',72,'src/azure/azure_http.cpp'):
        (0,'Production HTTP client implements two POST overloads and query encoding.',
         ((37,'client.Post(path, http_params)'),(58,'client.Post(path, body, content_type)'),(72,'std::string UrlEncode'))),
    ('hugr-lab/mssql-extension',72,'src/include/azure/azure_http.hpp'):
        (0,'Header defines a response type and declares the HTTP client interface.',
         ((19,'struct HttpResponse'),(25,'return error.empty()'),(34,'HttpResponse HttpPost'))),
    ('adibendahan/SimplyFilterSMS-iOS',29,'Simply Filter SMS/View Layer/Others/TipCardView.swift'):
        (0,'Production SwiftUI component renders tip purchase controls and their presentation state.',
         ((9,'struct TipCardView: View'),(34,'ProgressView()'),(62,'struct TipCardButtonStyle'))),
    ('adibendahan/SimplyFilterSMS-iOS',29,'UI Tests/XCUIElementExtensions.swift'):
        (0,'XCTest element extension provides two conditional interactions without defining test cases.',
         ((9,'extension XCUIElement'),(10,'public func conditionalTap'),(16,'public func conditionalSwipeUp'))),
    ('adibendahan/SimplyFilterSMS-iOS',29,'fastlane/Fastfile'):
        (0,'Fastlane lanes invoke existing screenshot capture tooling and do not define test cases.',
         ((5,'lane :iphone_screenshots'),(23,'capture_screenshots('),(39,'lane :screenshots'))),
    ('theoden8/webspace_app',398,'macos/Runner/ShortcutsPlugin.swift'):
        (0,'Application channel handler synchronizes sites and relays pending launches.',
         ((33,'setMethodCallHandler'),(67,'private func syncSites'),(102,'private func drainPendingLaunch'))),
    ('theoden8/webspace_app',398,'macos/Runner/WebSpaceAppIntents.swift'):
        (0,'Application implements site queries, launch intents and shortcuts.',
         ((61,'struct SiteEntityQuery: EntityQuery'),(130,'func perform()'),(148,'struct WebSpaceShortcuts'))),
    ('b0x42/prizm',32,'Prizm/Data/Network/Models/RawFolder.swift'):
        (0,'Codable network model declares folder fields.',((12,'struct RawFolder: Codable'),(14,'let name:'))),
    ('b0x42/prizm',32,'Prizm/Domain/Entities/Folder.swift'):
        (0,'Domain model declares a folder identity and name.',((5,'struct Folder: Identifiable'),(7,'let name:'))),
    ('b0x42/prizm',32,'Prizm/Domain/Entities/FolderTreeNode.swift'):
        (0,'Domain model builds and inserts nodes in a tree of folders.',
         ((13,'static func buildTree'),(24,'private static func insertNode'))),
}

for action, call in (
    ('CreateFolder','createFolder'), ('DeleteFolder','deleteFolder'),
    ('MoveItemToFolder','moveItemToFolder'), ('RenameFolder','renameFolder'),
):
    use_case = f'{action}UseCase'
    NEGATIVE_FILES[('b0x42/prizm',32,f'Prizm/Data/UseCases/{use_case}Impl.swift')] = (
        0,'Production use case delegates the folder operation to its repository.',
        ((3,f'final class {use_case}Impl'),(8,f'try await repository.{call}(')))
    NEGATIVE_FILES[('b0x42/prizm',32,f'Prizm/Domain/UseCases/{use_case}.swift')] = (
        0,'Domain protocol declares the folder operation interface.',
        ((4,f'protocol {use_case}'),(5,'func execute(')))
