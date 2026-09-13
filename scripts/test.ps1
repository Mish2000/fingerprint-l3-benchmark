[CmdletBinding()]
param([string]$CondaExe)
. (Join-Path $PSScriptRoot 'common.ps1')
$taskRoot = Get-Fpl3Root
$taskConda = Get-Fpl3Conda $CondaExe
$taskPrefix = Join-Path $taskRoot '.conda\dev'
Push-Location -LiteralPath $taskRoot
try {
    Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, 'python', '-I', '-B', '-m', 'pytest', '-q')
    Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, 'ruff', 'check', 'src', 'tests')
}
finally { Pop-Location }
