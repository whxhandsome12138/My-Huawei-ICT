@echo off
rem Serve the static demo page (demo/serve.py) without a console window.
rem ASCII + CRLF on purpose: cmd silently fails on LF-only line endings.
setlocal
set "ROOT=%~dp0..\.."
if "%DEMO_PORT%"=="" set "DEMO_PORT=9301"

set "PYW="
if exist "%ROOT%\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\.venv\Scripts\pythonw.exe"
if not defined PYW if exist "%ROOT%\mcp_server\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\mcp_server\.venv\Scripts\pythonw.exe"
if not defined PYW (
  echo [launch_demo] venv not found under %ROOT% ^(.venv or mcp_server\.venv^) 1>&2
  exit /b 1
)

cd /d "%ROOT%" || exit /b 2
"%PYW%" demo\serve.py --port %DEMO_PORT% >> demo.log 2>&1
exit /b 0
