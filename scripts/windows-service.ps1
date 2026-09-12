param(
    [ValidateSet("install", "start", "stop", "restart", "remove", "status")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Pip = Join-Path $ProjectRoot ".venv\Scripts\pip.exe"
$Service = Join-Path $ProjectRoot ".venv\Scripts\garage-lpr-service.exe"

if ($Action -eq "install") {
    if (-not (Test-Path $Python)) {
        py -3 -m venv (Join-Path $ProjectRoot ".venv")
    }
    & $Pip install -e "$ProjectRoot\backend[windows-service]"
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Node.js/npm is required to build the local administration UI."
    }
    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        npm ci
        npm run build
    }
    finally {
        Pop-Location
    }
    & $Service --startup auto install
    & $Service start
    Write-Host "Garage LPR installed and started: http://localhost:8080"
    exit 0
}

if (-not (Test-Path $Service)) {
    throw "Service launcher not found. Run: .\scripts\windows-service.ps1 install"
}

switch ($Action) {
    "start" { & $Service start }
    "stop" { & $Service stop }
    "restart" { & $Service restart }
    "remove" { & $Service stop; & $Service remove }
    "status" { & $Service status }
}
