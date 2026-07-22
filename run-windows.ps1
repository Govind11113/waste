# =============================================================================
# E-Waste Management -- Run the app (single-server mode)
# =============================================================================
# Usage (from the project root, in PowerShell):
#     .\run-windows.ps1
#
# Starts the FastAPI backend on http://127.0.0.1:8000. Because the frontend
# was built into frontend\dist\ during setup, the same server also serves the
# React app. Open http://127.0.0.1:8000 in your browser.
#
# Press Ctrl+C in this window to stop.
# ASCII-only on purpose so PowerShell parses it under any code page.
# =============================================================================

$ErrorActionPreference = 'Stop'
$ProjectRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir   = Join-Path $ProjectRoot 'backend'
$Py           = Join-Path $BackendDir '.venv\Scripts\python.exe'
$EnvFile      = Join-Path $BackendDir '.env'
$FrontendDist = Join-Path $ProjectRoot 'frontend\dist\index.html'

if (-not (Test-Path $Py)) {
    Write-Host 'Backend virtualenv is missing. Run .\setup-windows.ps1 first.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $EnvFile)) {
    Write-Host 'backend\.env is missing. Run .\setup-windows.ps1 first, then edit backend\.env with your Clerk keys.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $FrontendDist)) {
    Write-Host 'frontend\dist not found. Run: cd frontend; npm run build' -ForegroundColor Yellow
    Write-Host '(Or rerun .\setup-windows.ps1)' -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host 'Starting E-Waste Management on http://127.0.0.1:8000' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C to stop.' -ForegroundColor DarkGray
Write-Host ''

Set-Location $BackendDir
& $Py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
