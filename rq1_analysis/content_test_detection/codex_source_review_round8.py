"""Direct, complete-file source review of production code and configuration."""

SINGLE = {
    ('Yourdaylight/stock_datasource',31): (0,'Vue panel edits schedule settings, loads history, and triggers synchronization.',
        ((175,'store.fetchScheduleConfig()'),(185,'store.fetchScheduleHistory'),(225,'store.triggerScheduleNow()'))),
    ('Yourdaylight/stock_datasource',44): (0,'Vue interface fetches, filters, analyzes, archives and exports system logs.',
        ((58,'systemLogsApi.getLogs'),(115,'systemLogsApi.analyzeLogs'),(145,'systemLogsApi.exportLogs'))),
    ('strelov1/freehire',434): (0,'Svelte profile form extracts resume skills and saves the edited profile.',
        ((89,'await extractResumeSkills(file)'),(154,'async function submit'),(160,'profileStore.save(specializations, skills)'))),
    ('S2thend/cursor-history',1): (0,'Application parser decodes chat sessions and handles previews, search snippets and exports.',
        ((76,'export function parseChatData'),(290,'export function extractCodeBlocks'),(430,'export function exportToJson'))),
    ('BlackBeltTechnology/pi-agent-dashboard',169): (0,'React component parses YAML frontmatter and formats it for display.',
        ((31,'export function extractFrontmatter'),(152,'function ValueCell'),(337,'export function FrontmatterProperties'))),
    ('JawadAminMSFT/WorkbenchIQ',10): (0,'React components render structured chat responses and parse embedded JSON.',
        ((143,'export function RiskFactorsCard'),(336,'export function parseStructuredContent'),
         (406,'export function StructuredContentRenderer'))),
}

NEGATIVE_FILES = {
    ('Framstag/libosmscout',1716,'libosmscout/include/osmscout/feature/HighwayMilestoneFeature.h'):
        (0,'Production feature header declares milestone values, parsing, and serialization.',
         ((30,'class OSMSCOUT_API HighwayMilestoneFeatureValue'),(92,'void Read(FileScanner& scanner)'),(124,'void Parse(TagErrorReporter& reporter'))),
    ('Framstag/libosmscout',1716,'libosmscout/src/osmscout/feature/HighwayMilestoneFeature.cpp'):
        (0,'Production feature implementation reads and writes values and parses milestone tags.',
         ((28,'HighwayMilestoneFeatureValue::Read'),(36,'HighwayMilestoneFeatureValue::Write'),(107,'HighwayMilestoneFeature::Parse'))),
    ('Yourdaylight/stock_datasource',16,'frontend/src/views/login/LoginView.vue'):
        (0,'Vue form submits user login or registration and routes successful sign-ins.',
         ((41,'authStore.login'),(57,'authStore.register'),(92,'@submit="handleSubmit"'))),
    ('Yourdaylight/stock_datasource',16,'src/stock_datasource/modules/auth/schema.sql'):
        (0,'ClickHouse schema declares user and whitelist tables.',
         ((2,'CREATE TABLE IF NOT EXISTS users'),(15,'CREATE TABLE IF NOT EXISTS email_whitelist'))),
    ('halo-dev/halo',10133,'ui/console-src/modules/interface/menus/components/MenuItemParentSelect.vue'):
        (0,'Vue dropdown filters menu nodes and updates the selected parent.',
         ((49,'filterMenuItemTreeNodes'),(77,'function handleSelect'),(167,'@select="handleSelect"'))),
    ('halo-dev/halo',10133,'ui/console-src/modules/interface/menus/components/MenuItemParentSelectNode.vue'):
        (0,'Vue tree node recursively renders available menu items and emits a selection event.',
         ((34,"emit('select', menuItem.metadata.name)"),(47,'v-for="child in node.children"'))),
    ('hugr-lab/mssql-extension',21,'src/catalog/mssql_primary_key.cpp'):
        (0,'Production database metadata queries discover key columns and compute row IDs.',
         ((70,'static void ExecuteMetadataQuery'),(129,'PrimaryKeyInfo::ComputeRowIdType'),(150,'PrimaryKeyInfo::Discover'))),
    ('hugr-lab/mssql-extension',21,'src/include/catalog/mssql_primary_key.hpp'):
        (0,'Header declares database key metadata structures and discovery methods.',
         ((15,'struct PKColumnInfo'),(35,'struct PrimaryKeyInfo'),(66,'static PrimaryKeyInfo Discover'))),
    ('jdjingdian/StaticRouteHelper',3,'StaticRouter/Services/RouteUtils.swift'):
        (0,'IPv4 utility pads route destination strings for display.',
         ((19,'func normalizeIPv4Destination'),(23,'return destination + String(repeating:'))),
    ('jdjingdian/StaticRouteHelper',3,'StaticRouter/Services/SystemRouteReader.swift'):
        (0,'System routing utility reads the route table and decodes kernel entries.',
         ((24,'static func readRoutes'),(47,'static func parseRouteBuffer'),(136,'return SystemRouteEntry('))),
    ('pmndrs/react-spring',2423,'.github/publish-ci/next/.npmrc'):
        (0,'Entire npm configuration sets a dependency-resolution option.',
         ((1,'legacy-peer-deps=true'),)),
    ('pmndrs/react-spring',2423,'.npmrc'):
        (0,'Entire npm configuration sets the registry.',
         ((1,'registry=https://registry.npmjs.org/'),)),
    ('LuSrackhall/KeyTone',124,'frontend/src/components/album-selector/AlbumSignatureBadge.vue'):
        (0,'Vue badge fetches an album author image and renders it with a fallback.',
         ((84,'{{ authorName }}'),(130,'async function loadImage'),(142,'await GetAlbumFile'))),
    ('LuSrackhall/KeyTone',124,'frontend/src/components/album-selector/AlbumSignatureHoverCard.vue'):
        (0,'Vue hover card shows author information and emits an event to open details.',
         ((79,'v-if="isCardVisible"'),(298,'function onTriggerEnter'),(364,"emit('view-details')"))),
    ('complytime/complyctl',530,'.devcontainer/Containerfile'):
        (0,'Development container installs tooling and sets a non-root user.',
         ((4,'RUN dnf install'),(19,'RUN useradd'),(20,'USER devuser'))),
    ('complytime/complyctl',530,'.devcontainer/scripts/post-create.sh'):
        (0,'Container setup builds dependencies, installs providers, prepares fixtures and waits for the development registry.',
         ((34,'make build'),(92,'mkdir -p'),(109,'./bin/mock-oci-registry'),(166,'Dev environment ready.'))),
    ('OpenZeppelin/ui-builder',172,'scripts/rename/post-publish-verify.sh'):
        (0,'Release diagnostic prints registry availability and deprecation status for packages, with no failure decision for missing or wrong status.',
         ((37,'npm info "${pkg}" version'),(40,'echo "MISSING"'),(52,'echo "NOT DEPRECATED"'))),
    ('OpenZeppelin/ui-builder',172,'scripts/rename/update-legacy-packages.sh'):
        (0,'Publishing utility deprecates old packages and adds legacy tags. Read-only status reporting does not assert expected results.',
         ((94,'npm deprecate'),(97,'npm dist-tag add'),(110,'npm dist-tag ls "$OLD_NAME" || true'))),
    ('VadimOnix/xray-decky',1,'deploy.sh'):
        (0,'Deployment script builds the product and copies its output to the target device.',
         ((5,'pnpm run build'),(17,'cp -r dist'),(23,'rsync -avz'))),
    ('VadimOnix/xray-decky',1,'package-and-deploy.sh'):
        (0,'Deploy script builds, archives and uploads the package.',
         ((16,'pnpm run build'),(56,'zip -r "$ZIP_NAME"'),(65,'scp "$ZIP_PATH"'))),
}
