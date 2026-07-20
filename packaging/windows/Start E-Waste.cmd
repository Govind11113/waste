@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-EWaste.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo E-Waste Management stopped with exit code %EXIT_CODE%.
  if /I not "%~1"=="--no-pause" pause
)
exit /b %EXIT_CODE%
