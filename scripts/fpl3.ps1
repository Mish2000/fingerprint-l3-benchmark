# Stable project-root CLI; trailing arguments are forwarded without shell interpolation.
. (Join-Path $PSScriptRoot 'common.ps1')
$taskRoot = Get-Fpl3Root
$taskConda = Get-Fpl3Conda
$taskPrefix = Join-Path $taskRoot '.conda\dev'
$taskPython = Join-Path $taskPrefix 'python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run scripts\bootstrap.ps1 first.' }
Push-Location -LiteralPath $taskRoot
try {
    & $taskConda run --no-capture-output --prefix $taskPrefix $taskPython -I -B -m fpl3 @args
    $taskExit = $LASTEXITCODE
}
finally { Pop-Location }
exit $taskExit
