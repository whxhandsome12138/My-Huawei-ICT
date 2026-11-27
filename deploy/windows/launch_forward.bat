@echo off
rem TCP forward: expose a remote host:port on a local port (default 3300 -> 192.168.138.128:3000).
rem Override with FWD_LISTEN / FWD_TARGET, or pass extra args through to forward.py.
rem ASCII + CRLF on purpose: cmd silently fails on LF-only line endings.
setlocal
set "ROOT=%~dp0..\.."
if "%FWD_LISTEN%"=="" set "FWD_LISTEN=3300"
if "%FWD_TARGET%"=="" set "FWD_TARGET=192.168.138.128:3000"

set "PYW="
if exist "%ROOT%\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\.venv\Scripts\pythonw.exe"
if not defined PYW if exist "%ROOT%\mcp_server\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\mcp_server\.venv\Scripts\pythonw.exe"
if not defined PYW (
  echo [launch_forward] venv not found under %ROOT% ^(.venv or mcp_server\.venv^) 1>&2
  exit /b 1
)

cd /d "%~dp0" || exit /b 2
"%PYW%" forward.py --listen-port %FWD_LISTEN% --target %FWD_TARGET% %* >> forward.log 2>&1
exit /b 0
