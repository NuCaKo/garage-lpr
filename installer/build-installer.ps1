param(
    [string]$Version = "",
    [string]$SignTool = "",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$InstallerRoot = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $InstallerRoot
$BuildRoot = Join-Path $InstallerRoot "build"
$VirtualEnvironment = Join-Path $InstallerRoot ".venv"
$Python = Join-Path $VirtualEnvironment "Scripts\python.exe"
$FrontendOutput = Join-Path $BuildRoot "frontend-dist"
$ModelPayload = Join-Path $BuildRoot "model-payload"
$DistPath = Join-Path $BuildRoot "dist"
$WorkPath = Join-Path $BuildRoot "work"
$OutputPath = Join-Path $BuildRoot "output"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $VersionLine = Select-String -Path (Join-Path $ProjectRoot "backend\pyproject.toml") `
        -Pattern '^version\s*=\s*"([^"]+)"$' | Select-Object -First 1
    if (-not $VersionLine) {
        throw "Project version could not be read from backend\pyproject.toml."
    }
    $Version = $VersionLine.Matches[0].Groups[1].Value
}

if ($Version -notmatch '^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$') {
    throw "Version must be a semantic version, received: $Version"
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $OutputPath | Out-Null

if (-not (Test-Path $Python)) {
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PythonLauncher) {
        throw "Python 3.11 x64 is required to build the installer."
    }
    & py -3.11 -m venv $VirtualEnvironment
}

if (-not $SkipDependencyInstall) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -e "$ProjectRoot\backend[windows-service]"
    & $Python -m pip install -r (Join-Path $InstallerRoot "requirements-build.txt")
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js 20+ and npm are required to build the frontend."
}

Push-Location (Join-Path $ProjectRoot "frontend")
try {
    & npm ci
    & npm run build -- --outDir $FrontendOutput --emptyOutDir
}
finally {
    Pop-Location
}

if (Test-Path $ModelPayload) {
    Remove-Item -Recurse -Force $ModelPayload
}
New-Item -ItemType Directory -Force -Path $ModelPayload | Out-Null
Copy-Item -Path (Join-Path $ProjectRoot "models\*") -Destination $ModelPayload -Recurse -Force

$OnnxModels = Get-ChildItem -Path $ModelPayload -Filter *.onnx -File -Recurse
if (-not $OnnxModels) {
    Write-Warning "No ONNX models found. The installed system will stay fail-safe DEGRADED until models are supplied."
}

& $Python -m PyInstaller --noconfirm --clean --distpath $DistPath --workpath $WorkPath `
    (Join-Path $InstallerRoot "garage-lpr-service.spec")
& $Python -m PyInstaller --noconfirm --clean --distpath $DistPath --workpath $WorkPath `
    (Join-Path $InstallerRoot "garage-lpr-soak.spec")

$ServiceExecutable = Join-Path $DistPath "GarageLPRService\GarageLPRService.exe"
$SoakExecutable = Join-Path $DistPath "GarageLPRSoak.exe"
$MigrationVersion = Join-Path $DistPath `
    "GarageLPRService\_internal\garage_lpr\database\migrations\versions\7c23bbc53b1d_initial_foundation_schema.py"
$BundledFrontend = Join-Path $DistPath "GarageLPRService\_internal\frontend\dist\index.html"

foreach ($RequiredFile in @($ServiceExecutable, $SoakExecutable, $MigrationVersion, $BundledFrontend)) {
    if (-not (Test-Path $RequiredFile)) {
        throw "Required bundle file is missing: $RequiredFile"
    }
}

& $SoakExecutable --help | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "GarageLPRSoak.exe smoke test failed."
}

$InnoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $InnoCompiler) {
    $DefaultInnoCompiler = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    if (Test-Path $DefaultInnoCompiler) {
        $InnoCompiler = Get-Item $DefaultInnoCompiler
    }
}
if (-not $InnoCompiler) {
    throw "Inno Setup 6 compiler (ISCC.exe) was not found."
}

$InnoArguments = @(
    "/DAppVersion=$Version",
    "/O$OutputPath"
)
if (-not [string]::IsNullOrWhiteSpace($SignTool)) {
    $InnoArguments += "/DEnableSigning=1"
    $InnoArguments += "/Sgaragelpr=$SignTool"
}
$InnoArguments += (Join-Path $InstallerRoot "GarageLPR.iss")

& $InnoCompiler @InnoArguments
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

$InstallerExecutable = Join-Path $OutputPath "GarageLPR-Setup-$Version-x64.exe"
if (-not (Test-Path $InstallerExecutable)) {
    throw "Installer output is missing: $InstallerExecutable"
}

$Hash = Get-FileHash -Path $InstallerExecutable -Algorithm SHA256
Set-Content -Path "$InstallerExecutable.sha256" `
    -Value "$($Hash.Hash)  $($Hash.Path | Split-Path -Leaf)" -Encoding ascii

Write-Host "Installer ready: $InstallerExecutable"
Write-Host "SHA256: $($Hash.Hash)"
