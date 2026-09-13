[CmdletBinding()]
param([string]$CondaExe, [switch]$VerifyOnly)

. (Join-Path $PSScriptRoot 'common.ps1')
$taskRoot = Get-Fpl3Root
$taskConda = Get-Fpl3Conda $CondaExe

foreach ($taskProfile in @('dev', 'p1')) {
    $taskPrefix = Join-Path $taskRoot ".conda\$taskProfile"
    $taskPython = Join-Path $taskPrefix 'python.exe'
    $taskRequiredVersion = if ($taskProfile -eq 'dev') { '3.13.15' } else { '3.10.21' }
    if (-not (Test-Path -LiteralPath (Join-Path $taskPrefix 'conda-meta'))) {
        if ($VerifyOnly) { throw "Missing Conda profile: $taskProfile" }
        if (Test-Path -LiteralPath $taskPrefix) { throw "Refusing non-Conda existing path: $taskPrefix" }
        Invoke-Fpl3Checked $taskConda @('create', '--yes', '--override-channels', '--channel', 'conda-forge',
            '--strict-channel-priority', '--prefix', $taskPrefix, '--file',
            (Join-Path $taskRoot "environments\locks\$taskProfile-win-64.explicit.txt"))
    }
    Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, $taskPython, '-I', '-c',
        'import platform,sys; assert platform.python_version()==sys.argv[1], "Wrong profile Python"; print(sys.executable)', $taskRequiredVersion)
    if (-not $VerifyOnly) {
        if ($taskProfile -eq 'p1') {
            Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, $taskPython, '-I', '-m', 'pip',
                'install', '--no-deps', '-r', (Join-Path $taskRoot 'environments\locks\p1-pip.txt'))
        }
        Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, $taskPython, '-I', '-m', 'pip',
            'install', '--no-deps', '-e', $taskRoot)
    }
    Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, $taskPython, '-I', '-m', 'pip', 'check')
    Invoke-Fpl3Checked $taskConda @('run', '--no-capture-output', '--prefix', $taskPrefix, $taskPython, '-I', '-B', '-c',
        'import collections,importlib.metadata as m,pip,sysconfig; names=collections.Counter(d.metadata["Name"].lower().replace("_","-") for d in m.distributions(path=[sysconfig.get_path("purelib")])); assert all(n==1 for n in names.values()), "Duplicate installed package metadata: recreate the profile from its lock"; assert pip.__version__==m.version("pip")=="26.2.1", "Pip files and metadata disagree"; print("Installed package metadata is unique and pip matches its Conda version.")')
}
Write-Output 'Development and P1 Conda profiles are ready.'
