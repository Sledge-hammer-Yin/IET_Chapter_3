param(
    [ValidateSet('all','prepare','run','summarize','plot','test','install-rtklib')][string]$Action = 'all',
    [ValidateSet('all','Deep-Urban-1','Medium-Urban-1')][string]$Sequence = 'all',
    [ValidateSet('all','B1_ESKF','B2_ESKF_NIS','B3_GNSS_IMU_FGO')][string]$Method = 'all'
)
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $PSScriptRoot '..\.envs\b123\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Create the isolated environment described in README.md first.'
}
& $pythonExe (Join-Path $PSScriptRoot 'run.py') $Action --sequence $Sequence --method $Method
exit $LASTEXITCODE

