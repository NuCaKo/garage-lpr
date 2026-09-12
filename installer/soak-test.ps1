param(
    [double]$DurationHours = 72,
    [double]$IntervalSeconds = 60,
    [double]$WarmupMinutes = 10
)

$ErrorActionPreference = "Stop"
$Service = Get-CimInstance Win32_Service -Filter "Name='GarageLPR'"
if (-not $Service -or $Service.State -ne "Running" -or $Service.ProcessId -le 0) {
    throw "GarageLPR service is not running."
}

$Monitor = Join-Path $PSScriptRoot "GarageLPRSoak.exe"
$Report = Join-Path $env:ProgramData "GarageLPR\runtime\soak\latest.json"

& $Monitor `
    --pid $Service.ProcessId `
    --duration-hours $DurationHours `
    --interval-seconds $IntervalSeconds `
    --warmup-seconds ($WarmupMinutes * 60) `
    --report $Report

exit $LASTEXITCODE
