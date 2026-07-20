@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Diagnose-EWaste.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if /I not "%~1"=="--no-pause" pause
exit /b %EXIT_CODE%
