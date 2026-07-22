# =============================================================================
# E-Waste Management -- One-shot Windows setup
# =============================================================================
# Usage (from the project root, in PowerShell):
#     Set-ExecutionPolicy -Scope Process Bypass -Force
#     .\setup-windows.ps1
#
# What it does:
#   1. Verifies Python 3.11 x64 and Node.js are installed
#   2. Deletes macOS leftovers from the ZIP (venv, node_modules, __pycache__)
#   3. Creates backend virtualenv and installs Python dependencies
#   4. Creates backend .env from example (if missing)
#   5. Installs frontend npm packages
#   6. Creates frontend .env from example (if missing)
#   7. Builds the frontend for single-server mode
#   8. Tells you what to edit before first run
#
# Safe to re-run: skips work that's already done.
# ASCII-only on purpose so PowerShell parses it under any code page.
# =============================================================================

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir  = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }

# Remove-Item chokes on the broken macOS symlinks left in a ZIP created on
# macOS (e.g. backend\venv\bin\python3.lnk). Fall back to cmd's rd, which
# happily wipes any junction/symlink/file it finds. Redirect stderr INSIDE cmd
# via "2>nul" so PowerShell never sees the noise, then judge success purely by
# whether the path still exists.
function Remove-Tree($path) {
    if (-not (Test-Path -LiteralPath $path)) { return }
    try {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
        return
    } catch { }
    cmd.exe /c "rd /s /q `"$path`" 2>nul" | Out-Null
    if (Test-Path -LiteralPath $path) {
        throw "Could not remove $path. If this project lives in a Parallels/VMware shared folder (C:\Mac\...), copy it to a local Windows path (e.g. C:\dev\E-waste) and rerun setup."
    }
}

# -----------------------------------------------------------------------------
# 1. Prerequisites
# -----------------------------------------------------------------------------
Write-Step 'Checking prerequisites'

try   { $pyVer = (& py -3.11 --version) 2>&1; Write-Ok "Python: $pyVer" }
catch { Write-Fail 'Python 3.11 x64 not found. Install from https://www.python.org/downloads/release/python-3119/ and tick "Add python.exe to PATH".' }

try   { $nodeVer = (& node --version) 2>&1; Write-Ok "Node:   $nodeVer" }
catch { Write-Fail 'Node.js not found. Install LTS from https://nodejs.org/en/download' }

try   { $npmVer = (& npm --version) 2>&1; Write-Ok "npm:    $npmVer" }
catch { Write-Fail 'npm not found. Reinstall Node.js.' }

# -----------------------------------------------------------------------------
# 2. Clean macOS leftovers from the ZIP
# -----------------------------------------------------------------------------
Write-Step 'Cleaning macOS leftovers from ZIP'

$leftovers = @(
    (Join-Path $BackendDir  'venv'),
    (Join-Path $BackendDir  '.venv'),
    (Join-Path $FrontendDir 'node_modules'),
    (Join-Path $FrontendDir 'dist')
)
foreach ($path in $leftovers) {
    if (Test-Path -LiteralPath $path) {
        Remove-Tree $path
        Write-Ok "Removed $path"
    }
}
Get-ChildItem -Path $ProjectRoot -Recurse -Force -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Tree $_.FullName }
Write-Ok '__pycache__ folders removed'

# -----------------------------------------------------------------------------
# 3. Backend virtualenv + dependencies
# -----------------------------------------------------------------------------
Write-Step 'Installing backend (Python) dependencies -- this takes 5-10 minutes'

Push-Location $BackendDir
try {
    & py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Could not create backend virtualenv.' }
    Write-Ok 'Created backend\.venv'

    $py = Join-Path $BackendDir '.venv\Scripts\python.exe'
    & $py -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Fail 'pip upgrade failed.' }

    & $py -m pip install -r requirements-windows.txt
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Backend dependency install failed. Check your internet connection and retry.' }
    Write-Ok 'Backend dependencies installed'

    if (-not (Test-Path '.env')) {
        Copy-Item '.env.example' '.env'
        Write-Ok 'Created backend\.env from template (needs your Clerk values)'
    } else {
        Write-Ok 'backend\.env already exists -- left as-is'
    }
} finally { Pop-Location }

# -----------------------------------------------------------------------------
# 4. Frontend npm packages
# -----------------------------------------------------------------------------
Write-Step 'Installing frontend (npm) packages'

Push-Location $FrontendDir
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) { Write-Fail 'npm ci failed.' }
    Write-Ok 'npm packages installed'

    if (-not (Test-Path '.env')) {
        Copy-Item '.env.example' '.env'
        Write-Ok 'Created frontend\.env from template (needs your Clerk key)'
    } else {
        Write-Ok 'frontend\.env already exists -- left as-is'
    }

    Write-Step 'Building frontend for single-server mode'
    & npm run build
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Frontend build failed.' }
    Write-Ok 'Frontend built into frontend\dist\'
} finally { Pop-Location }

# -----------------------------------------------------------------------------
# 5. Done -- tell the user what's next
# -----------------------------------------------------------------------------
Write-Host ''
Write-Host '=====================================================================' -ForegroundColor Green
Write-Host ' Setup complete.' -ForegroundColor Green
Write-Host '=====================================================================' -ForegroundColor Green
Write-Host ''
Write-Host 'BEFORE FIRST RUN -- edit these two files with your Clerk keys:' -ForegroundColor Yellow
Write-Host "  1. $BackendDir\.env"
Write-Host '     Set EWASTE_CLERK_PUBLISHABLE_KEY  (pk_test_...)'
Write-Host '     Set CLERK_JWKS_URL              (https://<your>.clerk.accounts.dev/.well-known/jwks.json)'
Write-Host ''
Write-Host "  2. $FrontendDir\.env"
Write-Host '     Set VITE_CLERK_PUBLISHABLE_KEY  (same pk_test_... value)'
Write-Host ''
Write-Host 'Get those from https://clerk.com -- see WINDOWS_QUICKSTART.md step 2.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'TO START THE APP (from the project root):' -ForegroundColor Cyan
Write-Host '     .\run-windows.ps1'
Write-Host ''
Write-Host 'Then open http://127.0.0.1:8000 in your browser.'
Write-Host ''
