"""Direct source review of application code, migrations and test support."""

MAC_BRIDGE = 'src/Uno.UI.Runtime.Skia.MacOS/UnoNativeMac/UnoNativeMac'
IOS_APP = 'Simply Filter SMS'

NEGATIVE_FILES = {
    ('VadimOnix/xray-decky',15,'docs/plugin-page/index.html'):
        (0,'Static project site presents features, installation and troubleshooting sections.',
         ((46,'id="features-title"'),(97,'id="install-title"'),(195,'id="troubleshooting-title"'))),
    ('VadimOnix/xray-decky',15,'docs/plugin-page/scripts/optimize-images.sh'):
        (0,'Asset build script resizes and encodes images for publication.',
         ((14,'for W in 400 800 1200'),(16,'cwebp'),(28,'avifenc'))),
    ('unoplatform/uno',23288,f'{MAC_BRIDGE}/UNODragDrop.h'):
        (0,'Public header declares drag-and-drop data structures and platform callbacks.',
         ((21,'struct DragDropData'),(38,'struct DragSourceData'),(55,'void uno_window_register_for_drag_drop'))),
    ('unoplatform/uno',23288,f'{MAC_BRIDGE}/UNODragDrop.m'):
        (0,'Native bridge converts pasteboard data and starts AppKit drag sessions.',
         ((113,'info.draggingPasteboard'),(268,'BOOL uno_drag_start'),(411,'beginDraggingSessionWithItems'))),
    ('zhuanggenhua/BoardGame',80,'src/games/smashup/abilities/princesses.ts'):
        (0,'Game logic handles player interactions and registers faction abilities with the game engine.',
         ((156,'function princessesHappilyEverAfter'),(478,'export function registerPrincessesAbilities'),
          (728,'export function registerPrincessesInteractionHandlers'))),
    ('litara-app/litara',17,'apps/web/public/reader.html'):
        (0,'Browser reader implements display settings, search and document loading.',
         ((134,'function applyTheme'),(215,'async function runSearch'),(346,'await fetch(data.url'))),
    ('Yourdaylight/stock_datasource',93,'frontend/src/views/apiAccess/ApiAccessView.vue'):
        (0,'Vue administration view loads API usage and edits access policies.',
         ((101,'const loadUsage = async'),(186,'const handleSavePolicy = async'),(243,'<template>'))),
    ('Yourdaylight/stock_datasource',93,'src/stock_datasource/modules/open_api/schema.sql'):
        (0,'Schema defines API access settings and usage-log tables.',
         ((2,'CREATE TABLE IF NOT EXISTS api_access_policies'),(18,'CREATE TABLE IF NOT EXISTS api_usage_log'))),
    ('smart-mcp-proxy/mcpproxy-go',146,'frontend/src/components/AnnotationBadges.vue'):
        (0,'Vue component renders annotation badges and derives presentation classes.',
         ((58,'withDefaults(defineProps'),(76,'const badgeClasses'))),
    ('smart-mcp-proxy/mcpproxy-go',146,'frontend/src/views/Sessions.vue'):
        (0,'Vue application view loads sessions and formats timestamps for display.',
         ((169,'const loadSessions = async'),(192,'const formatRelativeTime'))),
    ('adibendahan/SimplyFilterSMS-iOS',28,f'{IOS_APP}/Framework Layer/Managers/Protocols/TipJarManagerProtocol.swift'):
        (0,'Swift protocol declares the tip jar manager interface.',
         ((15,'protocol TipJarManagerProtocol'),(18,'func purchase('))),
    ('adibendahan/SimplyFilterSMS-iOS',28,f'{IOS_APP}/Framework Layer/Managers/TipJarManager.swift'):
        (0,'StoreKit manager handles purchases, unfinished transactions and product loading.',
         ((38,'func purchase('),(70,'private func finishUnfinishedTransactions'),(78,'private func fetchProducts'))),
    ('adibendahan/SimplyFilterSMS-iOS',28,f'{IOS_APP}/View Layer/Others/ConfettiView.swift'):
        (0,'UIKit wrapper renders a particle animation.',
         ((9,'struct ConfettiView: UIViewRepresentable'),(51,'private func setupEmitter'))),
    ('adibendahan/SimplyFilterSMS-iOS',28,f'{IOS_APP}/View Layer/Screens/TipJarView.swift'):
        (0,'SwiftUI purchase screen implements view state and supplies a visual preview.',
         ((11,'struct TipJarView: View'),(237,'func purchase('),(283,'PreviewProvider'))),
    ('adibendahan/SimplyFilterSMS-iOS',28,'Tests/Mocks/mock_TipJarManager.swift'):
        (0,'Test double implements the purchase interface and exposes counters without defining test cases.',
         ((10,'class mock_TipJarManager'),(23,'func resetCounters'))),
    ('carverauto/threadr',159,'elixir/threadr/lib/threadr/ml/hybrid_retriever.ex'):
        (0,'Application retrieval module merges vector and lexical search and expands message matches.',
         ((54,'def search_messages'),(186,'defp merge_matches'),(257,'defp expand_matches'))),
    ('carverauto/threadr',159,'elixir/threadr/priv/repo/migrations/20260310033000_enable_pg_trgm_extension.exs'):
        (0,'Reversible database migration installs and removes the PostgreSQL extension.',
         ((5,'CREATE EXTENSION IF NOT EXISTS'),(9,'DROP EXTENSION IF EXISTS'))),
    ('carverauto/threadr',159,'elixir/threadr/priv/repo/tenant_migrations/20260310033100_add_message_trigram_indexes.exs'):
        (0,'Reversible database migration manages the tenant message index.',
         ((4,'def up do'),(13,'DROP INDEX IF EXISTS'))),
}
