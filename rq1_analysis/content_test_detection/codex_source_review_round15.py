"""Pinned review of installers, generation scripts and packaging tools."""

NEGATIVE_FILES = {
    ('automateyournetwork/netclaw',65,'scripts/checkpoint-enable.sh'):
        (0,'Installer builds MCP servers and reports whether expected build files exist.',
         ((90,'Building Check Point MCP servers'),(211,'if [ -f'),(221,'Verification:'))),
    ('automateyournetwork/netclaw',77,'scripts/twitter_install.sh'):
        (0,'Installer sets up dependencies and credentials and prints a suggestion for a manual check.',
         ((64,'Installing Python dependencies'),(85,'Configuring Twitter API credentials'),(209,'echo "  To test:'))),
    ('cnoe-io/ai-platform-engineering',1003,'scripts/generate-helm-chart-docs.sh'):
        (0,'Generator builds documentation and guards against prerelease version strings in generated output.',
         ((318,'generate_docusaurus_page()'),(419,'validate_no_rc_versions()'),(463,'generate_docusaurus_page "$chart_dir"'))),
    ('kusari-oss/darnit',240,'packaging/claude-plugin/build.sh'):
        (0,'Build script checks package layout, writes the bundle and lists the archive contents.',
         ((112,'expected_bundled'),(136,'zip -r'),(143,'unzip -l'))),
    ('kusari-oss/darnit',240,'packaging/claude-plugin/templates/darnit-mcp-runner'):
        (0,'Launcher dispatches the installed program through one of two package runners.',
         ((28,'try_uvx()'),(34,'try_pipx()'),(41,'try_pipx "$@"'))),
    ('smart-mcp-proxy/mcpproxy-go',158,'scripts/verify-oas.sh'):
        (0,'Regenerates OpenAPI artifacts and detects uncommitted changes to those artifacts.',
         ((13,'make swagger'),(16,'git status --porcelain'),(19,'OpenAPI artifacts are out of date'))),
}
