@echo off
setlocal
set "TOP10_BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%TOP10_BROWSER%" set "TOP10_BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%TOP10_BROWSER%" set "TOP10_BROWSER=%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"
set "TOP10_HTML=%~dp0top10.html"
set "TOP10_PROFILE=%LOCALAPPDATA%\InformationProcessingPractical\software-browser-profile"
if not exist "%TOP10_HTML%" (
  echo top10.html was not found next to this CMD file.
  pause
  exit /b 1
)
if not exist "%TOP10_BROWSER%" (
  echo Microsoft Edge was not found.
  pause
  exit /b 1
)
if /i "%~1"=="/check" (
  echo Launcher ready: top10.html
  exit /b 0
)
rem Use the same software-rendering profile as the existing study launchers.
start "" "%TOP10_BROWSER%" --disable-gpu --disable-gpu-compositing --new-window --no-first-run --no-default-browser-check --user-data-dir="%TOP10_PROFILE%" "%TOP10_HTML%"
exit /b %errorlevel%
