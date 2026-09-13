Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Fpl3Root {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
}

function Get-Fpl3Conda {
    param([string]$ExplicitPath)
    $taskCandidates = @()
    if ($ExplicitPath) { $taskCandidates += $ExplicitPath }
    if ($env:CONDA_EXE) { $taskCandidates += $env:CONDA_EXE }
    $taskLocalPath = Join-Path (Get-Fpl3Root) 'workspace\local.json'
    if (Test-Path -LiteralPath $taskLocalPath) {
        $taskLocal = Get-Content -LiteralPath $taskLocalPath -Raw | ConvertFrom-Json
        if ($taskLocal.PSObject.Properties['conda_executable']) { $taskCandidates += $taskLocal.conda_executable }
    }
    $taskCommand = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($taskCommand) { $taskCandidates += $taskCommand.Source }
    $taskCandidates += (Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe')
    $taskCandidates += (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe')
    foreach ($taskCandidate in $taskCandidates) {
        if (Test-Path -LiteralPath $taskCandidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $taskCandidate).Path
        }
    }
    throw 'Miniconda was not found. Pass -CondaExe with its conda executable.'
}

function Invoke-Fpl3Checked {
    param([string]$CondaExe, [string[]]$CondaArguments)
    & $CondaExe @CondaArguments
    if ($LASTEXITCODE -ne 0) { throw "Conda command failed with exit code $LASTEXITCODE" }
}
