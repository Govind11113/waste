@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Configure-EWaste.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Configuration did not complete successfully. Review the message above.
  if /I not "%~1"=="--no-pause" pause
)
exit /b %EXIT_CODE%
