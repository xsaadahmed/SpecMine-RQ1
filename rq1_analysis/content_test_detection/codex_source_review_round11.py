"""Pinned review of production interfaces, serialization and build checks."""

STOCK = 'Yourdaylight/stock_datasource'
FREEHIRE = 'strelov1/freehire'
VIBES = 'victorGPT/vibeusage'
DECENZA = 'Kulitorum/Decenza'

NEGATIVE_FILES = {
    (STOCK,65,'frontend/src/views/datamanage/KnowledgeView.vue'):
        (0,'Vue administration screen runs data synchronization and displays documents and sync history.',
         ((647,'const handleSync = async'),(699,'const fetchSyncHistory'),(709,'const fetchDocuments'))),
    (STOCK,15,'frontend/src/views/datamanage/components/TaskDetailDialog.vue'):
        (0,'Vue dialog displays details of a data task and emits visibility changes.',
         ((16,"emit('update:visible'"),(143,'task.trade_dates.slice'))),
    (STOCK,15,'frontend/src/views/etf/EtfScreenerView.vue'):
        (0,'Vue screener presents ETFs and opens their detail and analysis panels.',
         ((175,'v-for="etf in commonEtfs"'),(313,'v-model:visible="showDetailDialog"'),(321,'showAnalysisPanel'))),
    (STOCK,15,'frontend/src/views/etf/components/EtfAnalysisPanel.vue'):
        (0,'Vue panel displays analysis signals and captures questions for the ETF interface.',
         ((60,'v-model="activeTab"'),(191,'etfStore.quickAnalysis.signals'),(244,'v-model="aiQuestion"'))),
    (STOCK,15,'frontend/src/views/etf/components/EtfDetailDialog.vue'):
        (0,'Vue dialog renders ETF details and emits close and analysis actions.',
         ((43,"emit('update:visible'"),(49,"emit('analyze', etfInfo.value)"))),
    (FREEHIRE,330,'migrations/0032_saved_searches_public_slug.sql'):
        (0,'SQL migration adds sharing fields and an index to saved searches.',
         ((12,'ALTER TABLE saved_searches'),(19,'CREATE UNIQUE INDEX IF NOT EXISTS saved_searches_public_slug_idx'))),
    (FREEHIRE,330,'web/src/lib/components/SavedSearchesView.svelte'):
        (0,'Saved search interface loads searches and provides sharing and link copying.',
         ((22,'async function load()'),(54,'async function confirmShare'),(103,'navigator.clipboard.writeText'))),
    (FREEHIRE,330,'web/src/routes/b/[slug]/+page.svelte'):
        (0,'Public board page renders job entries and loads more results.',
         ((28,'<title>{board.name}'),(46,'{#each jobs.items as job'),(54,'jobs.loadMore()'))),
    (FREEHIRE,330,'web/src/routes/my/searches/+page.svelte'):
        (0,'Saved searches route sets the page title and mounts the saved searches view.',
         ((6,'<title>Saved searches'),(12,'<SavedSearchesView />'))),
    (VIBES,36,'dashboard/share.html'):
        (0,'Static sharing template supplies page title and Open Graph metadata.',
         ((6,'<title>__VIBESCORE_TITLE__'),(11,'property="og:image"'))),
    (VIBES,36,'dashboard/src/pages/AnnualPosterPage.jsx'):
        (0,'React dashboard handles date ranges and renders the annual usage poster.',
         ((55,'function getWeeksForRange'),(78,'/.test(trimmed)'),(91,'export function AnnualPosterPage'))),
    (VIBES,36,'dashboard/wrapped-2025.html'):
        (0,'HTML landing template supplies metadata and redirects to the dashboard.',
         ((9,'property="og:title"'),(53,'window.location.hostname'),(59,'window.location.replace'))),
    (DECENZA,951,'src/history/shothistorystorage_internal.cpp'):
        (0,'Storage helper parses stored profile JSON and prepares shot-analysis inputs.',
         ((18,'QJsonDocument::fromJson'),(22,'Profile::fromJson'),(34,'ShotSummarizer::getAnalysisFlags'))),
    (DECENZA,951,'src/history/shothistorystorage_internal.h'):
        (0,'Internal header declares shot-profile and analysis structures.',
         ((19,'struct ProfileFrameInfo'),(36,'struct AnalysisInputs'))),
    (DECENZA,951,'src/history/shothistorystorage_serialize.cpp'):
        (0,'Production serializer converts recorded shot data and analyzes phases for display.',
         ((22,'ShotHistoryStorage::convertShotRecord'),(122,'ShotAnalysis::analyzeShot'),(195,'phaseSummariesDoc'))),
    (DECENZA,1101,'src/ui/jscanvascontext.cpp'):
        (0,'Canvas implementation records drawing operations and resets frame state.',
         ((28,'JsCanvasContext::beginPath'),(65,'JsCanvasContext::fill'),(180,'JsCanvasContext::resetForNextFrame'))),
    (DECENZA,1101,'src/ui/jscanvascontext.h'):
        (0,'Header exposes QML drawing commands, context and gradient types.',
         ((20,'struct DrawCmd'),(54,'class JsCanvasContext : public QObject'),(126,'class JsCanvasGradient'))),
    (DECENZA,1101,'src/ui/jscanvaspainteritem.cpp'):
        (0,'Qt renderer replays drawing commands and schedules canvas repaint.',
         ((65,'class JsCanvasPainterItemRenderer'),(90,'std::as_const(m_cmds)'),(160,'JsCanvasPainterItem::requestPaint'))),
    (DECENZA,1101,'src/ui/jscanvaspainteritem.h'):
        (0,'Qt item interface declares canvas rendering and repaint methods.',
         ((12,'class JsCanvasPainterItem : public QCanvasPainterItem'),(19,'void requestPaint()'))),
    ('cardano-foundation/cardano-wallet',5279,'llm/reviews/5279/gate.sh'):
        (0,'Review gate invokes Bash syntax checking, ShellCheck and a Nix build without exercising application behavior.',
         ((8,'bash -n'),(10,'./scripts/shellcheck.sh'),(11,'nix build --quiet'))),
}
