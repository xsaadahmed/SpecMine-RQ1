"""Recognize a narrow standalone test harness without executing its source."""
import base64
import json
import re
import shutil
import subprocess


AST_CHECK = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
$text = [Console]::In.ReadToEnd()
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput(
    $text, [ref]$tokens, [ref]$errors)
if ($errors.Count -or -not $ast.EndBlock) { '[]'; exit }
$statements = $ast.EndBlock.Statements
$definitions = @($statements | Where-Object {
    $_ -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $_.Name -eq 'Write-Fail'
})
if ($definitions.Count -ne 1) { '[]'; exit }
$failBody = $definitions[0].Body.EndBlock.Statements
if (-not $failBody.Count -or
    $failBody[-1] -isnot [System.Management.Automation.Language.ExitStatementAst] -or
    $failBody[-1].Pipeline.Extent.Text -cne '1') { '[]'; exit }
$lines = @()
foreach ($statement in $statements) {
    if ($statement -isnot [System.Management.Automation.Language.IfStatementAst] -or
        $statement.Clauses.Count -ne 1) { continue }
    $condition, $block = $statement.Clauses[0].Item1, $statement.Clauses[0].Item2
    if ($condition.PipelineElements.Count -ne 1 -or $block.Statements.Count -ne 1) { continue }
    $expression = $condition.PipelineElements[0].Expression
    if ($expression -isnot [System.Management.Automation.Language.BinaryExpressionAst] -or
        $expression.Operator.ToString() -notin @('Ine','Cne','Inotmatch','Cnotmatch') -or
        $expression.Left -isnot [System.Management.Automation.Language.VariableExpressionAst]) { continue }
    $failure = $block.Statements[0]
    if ($failure.PipelineElements.Count -ne 1) { continue }
    $command = $failure.PipelineElements[0]
    if ($command -is [System.Management.Automation.Language.CommandAst] -and
        $command.GetCommandName() -ceq 'Write-Fail') {
        $lines += $command.Extent.StartLineNumber
    }
}
ConvertTo-Json -InputObject $lines -Compress
"""


def standalone_assertions(source):
    if not all(marker in source for marker in ('function Write-Fail', 'exit 1', 'Write-Pass')):
        return []
    shell = shutil.which('pwsh')
    if not shell:
        return []
    command = base64.b64encode(AST_CHECK.encode('utf-16-le')).decode('ascii')
    try:
        output = subprocess.run(
            [shell, '-NoProfile', '-NonInteractive', '-EncodedCommand', command],
            input=source.encode(), capture_output=True, timeout=8, check=True,
        )
        lines = json.loads(output.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    if not isinstance(lines, list) or not all(type(i) is int for i in lines):
        return []
    source_lines = source.splitlines()
    markers = {}
    for number in lines:
        for line in reversed(source_lines[max(0, number - 6):number - 1]):
            if match := re.fullmatch(r'\s*#\s*Test\s+(\d+):\s+\S.*', line):
                markers.setdefault(match[1], number)
                break
    return list(markers.values())
