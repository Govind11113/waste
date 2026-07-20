[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$InstallRoot = Split-Path -Parent $PSScriptRoot
$Executable = Join-Path $InstallRoot 'EWasteManagement.exe'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    Write-Host "ERROR: EWasteManagement.exe is missing from $InstallRoot" -ForegroundColor Red
    exit 1
}

Set-Location -LiteralPath $InstallRoot
$Arguments = @('serve', '--port', $Port)
if ($NoBrowser) { $Arguments += '--no-browser' }
& $Executable @Arguments
exit $LASTEXITCODE
