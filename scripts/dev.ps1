$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3.11 -m venv (Join-Path $ProjectDir ".venv")
    & $Python -m pip install -e "$ProjectDir\backend[dev]"
}

if (-not (Test-Path (Join-Path $ProjectDir "frontend\node_modules"))) {
    npm --prefix (Join-Path $ProjectDir "frontend") install
}

& $Python -m alembic -c (Join-Path $ProjectDir "backend\alembic.ini") upgrade head
Start-Process npm -ArgumentList "--prefix", (Join-Path $ProjectDir "frontend"), "run", "dev"
& $Python -m garage_lpr
