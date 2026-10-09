@echo off
setlocal
set "PS1=%TEMP%\MRI_AI_CLEANUP_20261009.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/uMRI-web/uMRI-web.github.io/main/tract-viewer/tools/mri-ai-study-cleanup/MRI_AI_CLEANUP_20261009.ps1' -OutFile '%PS1%'"
if errorlevel 1 (
  echo Failed to download cleanup script.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
echo.
echo Press any key to close...
pause >nul
