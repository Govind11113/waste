[CmdletBinding()]
param(
    [string]$Version = '3.0.0',
    [switch]$SkipTests,
    [switch]$SkipModelDownload,
    [switch]$SkipSmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-LastExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem) {
    throw 'This release must be built natively on Windows 10/11 x64.'
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BackendRoot = Join-Path $ProjectRoot 'backend'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$BuildRoot = Join-Path $ProjectRoot 'build\windows'
$BuildVenv = Join-Path $BuildRoot '.venv'
$BuildPython = Join-Path $BuildVenv 'Scripts\python.exe'
$WorkRoot = Join-Path $BuildRoot 'pyinstaller'
$DistRoot = Join-Path $BuildRoot 'dist'
$StageName = "EWasteManagement-Windows-x64-v$Version"
$Stage = Join-Path $BuildRoot "stage\$StageName"
$ReleaseRoot = Join-Path $ProjectRoot 'release'
$Archive = Join-Path $ReleaseRoot "$StageName.zip"
$Spec = Join-Path $ProjectRoot 'packaging\windows\EWasteManagement.spec'

$Py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if ($null -ne $Py) {
    $BootstrapPython = $Py.Source
    $BootstrapPrefix = @('-3.11')
} else {
    $Python = Get-Command 'python.exe' -ErrorAction SilentlyContinue
    if ($null -eq $Python) { throw 'Python 3.11 x64 is required on the build PC.' }
    $BootstrapPython = $Python.Source
    $BootstrapPrefix = @()
}

& $BootstrapPython @BootstrapPrefix -c "import platform,sys; assert sys.version_info[:2] == (3,11), sys.version; assert platform.architecture()[0] == '64bit'; print(sys.version)"
Assert-LastExit 'Python 3.11 x64 prerequisite check'
if ($null -eq (Get-Command 'node.exe' -ErrorAction SilentlyContinue) -or $null -eq (Get-Command 'npm.cmd' -ErrorAction SilentlyContinue)) {
    throw 'Node.js and npm are required on the build PC.'
}

New-Item -ItemType Directory -Force -Path $BuildRoot, $ReleaseRoot | Out-Null
if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
    & $BootstrapPython @BootstrapPrefix -m venv $BuildVenv
    Assert-LastExit 'Windows build virtual environment creation'
}
& $BuildPython -m pip install --upgrade 'pip==26.1.2'
Assert-LastExit 'Pinned pip installation'
& $BuildPython -m pip install --requirement (Join-Path $BackendRoot 'requirements-windows.txt')
Assert-LastExit 'Windows build dependency installation'

$HadViteKey = Test-Path Env:VITE_CLERK_PUBLISHABLE_KEY
$SavedViteKey = $env:VITE_CLERK_PUBLISHABLE_KEY
Remove-Item Env:VITE_CLERK_PUBLISHABLE_KEY -ErrorAction SilentlyContinue
try {
    Push-Location $FrontendRoot
    try {
        & npm.cmd ci
        Assert-LastExit 'Frontend npm ci'
        if (-not $SkipTests) {
            & npm.cmd run typecheck
            Assert-LastExit 'Frontend typecheck'
            & npm.cmd test
            Assert-LastExit 'Frontend unit tests'
        }
        & npm.cmd run build
        Assert-LastExit 'Frontend production build'
    } finally {
        Pop-Location
    }

    Push-Location $BackendRoot
    try {
        if (-not $SkipTests) {
            & $BuildPython -m pytest -q
            Assert-LastExit 'Backend test suite'
            & $BuildPython scripts\test_classifier.py
            Assert-LastExit 'Deterministic classifier checks'
        }
        if (-not $SkipModelDownload) {
            & $BuildPython scripts\prepare_classifier_model.py
            Assert-LastExit 'Pinned classifier snapshot preparation'
        }
        & $BuildPython scripts\prepare_classifier_model.py --verify-only
        Assert-LastExit 'Classifier model manifest verification'
        & $BuildPython -c "from pathlib import Path; from app.runtime import verify_file_manifest; ok, errors = verify_file_manifest(Path('models/lifespan')); assert ok, errors; print('Lifespan model manifest verified')"
        Assert-LastExit 'Lifespan model manifest verification'
    } finally {
        Pop-Location
    }

    foreach ($GeneratedPath in @($WorkRoot, $DistRoot, $Stage)) {
        if (Test-Path -LiteralPath $GeneratedPath) {
            Remove-Item -LiteralPath $GeneratedPath -Recurse -Force
        }
    }
    New-Item -ItemType Directory -Force -Path $WorkRoot, $DistRoot, $Stage | Out-Null

    & $BuildPython -m PyInstaller --noconfirm --clean --workpath $WorkRoot --distpath $DistRoot $Spec
    Assert-LastExit 'PyInstaller one-folder build'

    $FrozenRoot = Join-Path $DistRoot 'EWasteManagement'
    if (-not (Test-Path -LiteralPath (Join-Path $FrozenRoot 'EWasteManagement.exe') -PathType Leaf)) {
        throw 'PyInstaller did not produce EWasteManagement.exe.'
    }
    Copy-Item -Path (Join-Path $FrozenRoot '*') -Destination $Stage -Recurse -Force
    Copy-Item -Path (Join-Path $ProjectRoot 'packaging\windows\*.cmd') -Destination $Stage -Force
    Copy-Item -Path (Join-Path $ProjectRoot 'packaging\windows\scripts') -Destination $Stage -Recurse -Force
    foreach ($Document in @('WINDOWS_INSTALL.md', 'WINDOWS_ACCEPTANCE.md', 'THIRD_PARTY_NOTICES.md')) {
        $DocumentPath = Join-Path $ProjectRoot $Document
        if (-not (Test-Path -LiteralPath $DocumentPath -PathType Leaf)) {
            throw "Required release document is missing: $Document"
        }
        Copy-Item -LiteralPath $DocumentPath -Destination $Stage -Force
    }

    $Blocked = Get-ChildItem -LiteralPath $Stage -Recurse -Force -File | Where-Object {
        $_.Name -eq '.env' -or $_.Name -like '.env.*' -or $_.Extension -in @('.db', '.sqlite', '.log')
    }
    if ($Blocked) {
        throw "Mutable or secret files entered the release stage: $($Blocked.FullName -join ', ')"
    }

    if (-not $SkipSmokeTest) {
        $OriginalLocalAppData = $env:LOCALAPPDATA
        $SmokeState = Join-Path $BuildRoot 'smoke-localappdata'
        if (Test-Path -LiteralPath $SmokeState) { Remove-Item -LiteralPath $SmokeState -Recurse -Force }
        $SmokeConfigDir = Join-Path $SmokeState 'EWasteManagement\config'
        New-Item -ItemType Directory -Force -Path $SmokeConfigDir | Out-Null
        $SmokeConfig = @"
EWASTE_CLERK_PUBLISHABLE_KEY="pk_test_build-smoke"
CLERK_JWKS_URL="https://build-smoke.clerk.accounts.dev/.well-known/jwks.json"
ALLOWED_ORIGINS="http://127.0.0.1:8765"
EWASTE_MODEL="siglip2-base"
HF_HUB_OFFLINE="1"
"@
        [IO.File]::WriteAllText((Join-Path $SmokeConfigDir '.env'), $SmokeConfig, (New-Object Text.UTF8Encoding($false)))

        $Listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
        $Listener.Start()
        $SmokePort = ([Net.IPEndPoint]$Listener.LocalEndpoint).Port
        $Listener.Stop()
        $SmokeOut = Join-Path $BuildRoot 'smoke.stdout.log'
        $SmokeErr = Join-Path $BuildRoot 'smoke.stderr.log'
        Remove-Item $SmokeOut, $SmokeErr -ErrorAction SilentlyContinue
        $env:LOCALAPPDATA = $SmokeState
        $Process = $null
        try {
            $Process = Start-Process -FilePath (Join-Path $Stage 'EWasteManagement.exe') `
                -ArgumentList @('serve', '--no-browser', '--port', $SmokePort) `
                -WorkingDirectory $Stage -PassThru -RedirectStandardOutput $SmokeOut -RedirectStandardError $SmokeErr
            $Deadline = (Get-Date).AddMinutes(10)
            $Ready = $false
            while ((Get-Date) -lt $Deadline) {
                if ($Process.HasExited) { break }
                try {
                    $Readiness = Invoke-RestMethod -Uri "http://127.0.0.1:$SmokePort/health/ready" -TimeoutSec 5
                    if ($Readiness.status -eq 'ready') { $Ready = $true; break }
                } catch { }
                Start-Sleep -Milliseconds 750
                $Process.Refresh()
            }
            if (-not $Ready) {
                $OutputTail = if (Test-Path $SmokeOut) { (Get-Content $SmokeOut -Tail 40) -join "`n" } else { '' }
                $ErrorTail = if (Test-Path $SmokeErr) { (Get-Content $SmokeErr -Tail 40) -join "`n" } else { '' }
                throw "Frozen release did not become ready.`nSTDOUT:`n$OutputTail`nSTDERR:`n$ErrorTail"
            }
            $Live = Invoke-RestMethod -Uri "http://127.0.0.1:$SmokePort/health/live" -TimeoutSec 10
            if ($Live.status -ne 'online') { throw 'Frozen liveness response was invalid.' }
            $Config = Invoke-RestMethod -Uri "http://127.0.0.1:$SmokePort/api/runtime-config" -TimeoutSec 10
            if (-not $Config.configured) { throw 'Frozen runtime configuration endpoint was not configured.' }
            $DeepLink = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$SmokePort/privacy" -TimeoutSec 10
            if ($DeepLink.StatusCode -ne 200 -or $DeepLink.Content -notmatch 'id=.root') {
                throw 'Frozen SPA deep-link smoke test failed.'
            }
            Write-Host 'Frozen localhost smoke test passed.' -ForegroundColor Green
        } finally {
            if ($null -ne $Process -and -not $Process.HasExited) {
                Stop-Process -Id $Process.Id -Force
                $Process.WaitForExit()
            }
            $env:LOCALAPPDATA = $OriginalLocalAppData
        }
    }

    & $BuildPython (Join-Path $BackendRoot 'scripts\package_windows_release.py') --stage $Stage --output $Archive
    Assert-LastExit 'ZIP release packaging and integrity check'
    Write-Host "Windows release completed: $Archive" -ForegroundColor Green
} finally {
    if ($HadViteKey) {
        $env:VITE_CLERK_PUBLISHABLE_KEY = $SavedViteKey
    } else {
        Remove-Item Env:VITE_CLERK_PUBLISHABLE_KEY -ErrorAction SilentlyContinue
    }
}
