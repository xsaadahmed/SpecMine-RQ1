"""Pinned review of market and iOS interfaces and screenshot tooling."""

MARKET = 'frontend/src/components/market'
IOS = 'Simply Filter SMS/View Layer/Others'

MARKET_FILES = {
    'IndexCompareChart.vue': ('Loads comparison data and handles chart range changes.', ((125,'const fetchIndexData'),(188,'const handleDateRangeChange'))),
    'MarketAiDialog.vue': ('Handles chat submission and clearing in the market dialog.', ((48,'const handleSend'),(73,'const handleClear'))),
    'MarketAiFloatButton.vue': ('Emits a click and renders a floating button.', ((11,"emit('click')"),(21,'@click="handleClick"'))),
    'SectorDetailDialog.vue': ('Loads sector details when its dialog opens.', ((109,'const handleOpened'),(133,'<template>'))),
    'SectorHeatmap.vue': ('Fetches sector data for the heatmap.', ((144,'const fetchData'),(192,'<template>'))),
    'SectorRankingTable.vue': ('Fetches sector rankings and renders table columns.', ((57,'const fetchData'),(155,'#pct_change'))),
}

IOS_FILES = {
    'EnableExtensionStepProtocol.swift': ('Declares fields for onboarding steps.', ((10,'protocol EnableExtensionStepProtocol'),(12,'var title'))),
    'EnableReportingExtensionStep.swift': ('Defines onboarding step order and localized instruction text.', ((10,'enum EnableReportingExtensionStep'),(103,'var description'))),
    'InstantTouchDisabler.swift': ('Wraps UIKit behavior for controlling touch input.', ((13,'struct InstantTouchDisabler'),(23,'func updateUIView'))),
    'PressDetector.swift': ('Connects a UIKit long-press recognizer to the view.', ((11,'struct PressDetector'),(42,'func handleGesture'))),
    'RefreshControlDisabler.swift': ('Wraps UIKit behavior for disabling refresh controls.', ((11,'struct RefreshControlDisabler'),(19,'func updateUIView'))),
    'ReportSubmitCard.swift': ('Renders submission state and animates the success indicator.', ((14,'struct ReportSubmitCard'),(136,'func transitionToSuccess'))),
    'SpinningLoaderView.swift': ('Implements and resets the loading animation.', ((12,'struct SpinningLoaderView'),(82,'func reset'))),
}

NEGATIVE_FILES = {
    ('Yourdaylight/stock_datasource',20,f'{MARKET}/{file}'): (0,reason,anchors)
    for file,(reason,anchors) in MARKET_FILES.items()
}
NEGATIVE_FILES.update({
    ('adibendahan/SimplyFilterSMS-iOS',35,f'{IOS}/{file}'): (0,reason,anchors)
    for file,(reason,anchors) in IOS_FILES.items()
})
NEGATIVE_FILES[('adibendahan/SimplyFilterSMS-iOS',35,'screenshots.sh')] = (
    0,'Runs an existing screenshot case under different simulator locales without defining a test case.',
    ((6,'TEST_ID='),(37,'xcodebuild test'),(41,'-only-testing "$TEST_ID"')),
)
