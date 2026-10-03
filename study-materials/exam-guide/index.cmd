@echo off
setlocal
set "EXAM_BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EXAM_BROWSER%" set "EXAM_BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EXAM_BROWSER%" set "EXAM_BROWSER=%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"
set "EXAM_HTML=%~dp0index.html"
set "EXAM_PROFILE=%LOCALAPPDATA%\InformationProcessingPractical\software-browser-profile"
if not exist "%EXAM_BROWSER%" (
  echo Microsoft Edge was not found.
  pause
  exit /b 1
)
if not exist "%EXAM_HTML%" (
  echo The HTML file was not found next to this CMD file.
  pause
  exit /b 1
)
if /i "%~1"=="/check" (
  echo Launcher ready: index.html
  exit /b 0
)
rem A separate profile keeps this launch apart from existing GPU-enabled sessions.
start "" "%EXAM_BROWSER%" --disable-gpu --disable-gpu-compositing --new-window --no-first-run --no-default-browser-check --user-data-dir="%EXAM_PROFILE%" "%EXAM_HTML%"
exit /b %errorlevel%
