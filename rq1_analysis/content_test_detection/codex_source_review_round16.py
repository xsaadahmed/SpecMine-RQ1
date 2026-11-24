"""Pinned verification markers, feature scaffolding and a registry smoke test."""

FLUTTER = 'gmeligio/flutter-docker-image'

MULTI = {
    (FLUTTER,499): ('script/verify_published_image.sh',
        'Standalone smoke test checks that a published image manifest is accessible anonymously, passing on HTTP 200 and failing otherwise.',
        ((35,'headers="$(curl'),(38,'"$status" == "200"'),(61,'"$retry_status" == "200"'),(72,'exit 1'))),
}

MARKERS = (
    (375,'2026-05-09-finish-cue-version-update'),
    (502,'2026-06-18-p15-codegen-docs-and-examples'),
    (502,'2026-06-18-p16-generators-cover-web-and-tool-lists'),
    (472,'2026-05-27-fix-android-buildtools-resolution'),
    (503,'2026-06-20-readme-platform-tool-lists'),
    (460,'2026-05-23-migrate-docs-src-to-pnpm'),
)

NEGATIVE_FILES = {
    (FLUTTER,pr,f'openspec/changes/archive/{folder}/.verify-passed'):
        (0,'One-line status marker records a prior verification without containing any executable code.',((1,'passed'),))
    for pr,folder in MARKERS
}
NEGATIVE_FILES.update({
    (repo,pr,'.specify/scripts/bash/create-new-feature.sh'):
        (0,'Feature scaffolder copies a specification template and reports generated paths.',
         ((284,'SPEC_FILE='),(285,'cp "$TEMPLATE"'),(294,'echo "SPEC_FILE:')))
    for repo,pr in [('safe-global/safe-wallet-monorepo',6936),('bitovi/cascade-mcp',86)]
})
