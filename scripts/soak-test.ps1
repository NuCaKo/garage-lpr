param(
    [double]$DurationHours = 72,
    [double]$IntervalSeconds = 60,
    [double]$WarmupMinutes = 10,
    [int]$TargetProcessId = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Monitor = Join-Path $ProjectRoot ".venv\Scripts\garage-lpr-soak.exe"
$Report = Join-Path $ProjectRoot "runtime\soak\latest.json"

if (-not (Test-Path $Monitor)) {
    throw "Soak monitor not found. Install the backend first."
}

if ($TargetProcessId -le 0) {
    $GarageService = Get-CimInstance Win32_Service -Filter "Name='GarageLPR'"
    if ($null -eq $GarageService -or $GarageService.State -ne "Running") {
        throw "GarageLPR Windows service is not running."
    }
    $TargetProcessId = [int]$GarageService.ProcessId
}

Write-Host "Monitoring Garage LPR PID $TargetProcessId for $DurationHours hour(s)."
& $Monitor `
    --pid $TargetProcessId `
    --duration-hours $DurationHours `
    --interval-seconds $IntervalSeconds `
    --warmup-minutes $WarmupMinutes `
    --report $Report
exit $LASTEXITCODE
