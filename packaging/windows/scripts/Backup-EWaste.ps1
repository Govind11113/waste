[CmdletBinding()]
param(
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$InstallRoot = Split-Path -Parent $PSScriptRoot
$Executable = Join-Path $InstallRoot 'EWasteManagement.exe'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    Write-Host "ERROR: EWasteManagement.exe is missing from $InstallRoot" -ForegroundColor Red
    exit 1
}

$Arguments = @('backup')
if (-not [string]::IsNullOrWhiteSpace($Output)) {
    $Arguments += @('--output', $Output)
}
& $Executable @Arguments
if ($LASTEXITCODE -eq 0) {
    Write-Host 'Keep backup ZIPs private: they include local history and may include configuration secrets.' -ForegroundColor Yellow
}
exit $LASTEXITCODE
