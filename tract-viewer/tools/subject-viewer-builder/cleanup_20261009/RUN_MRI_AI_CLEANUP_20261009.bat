@echo off
setlocal
set "ROOT=D:\MRI-AI-study"
set "PS1=%ROOT%\09_TOOLS\MRI_AI_CLEANUP_20261009.ps1"

if not exist "%ROOT%\09_TOOLS" mkdir "%ROOT%\09_TOOLS"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/uMRI-web/uMRI-web.github.io/main/tract-viewer/tools/subject-viewer-builder/cleanup_20261009/MRI_AI_CLEANUP_20261009.ps1' -OutFile '%PS1%'"

if errorlevel 1 (
  echo ERROR: Could not download cleanup script.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
echo.
pause
