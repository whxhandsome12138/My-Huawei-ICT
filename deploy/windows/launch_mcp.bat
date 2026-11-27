@echo off
rem Launch the MCP server (mcp_server/server.py) without a console window.
rem ASCII + CRLF on purpose: cmd silently fails on LF-only line endings.
setlocal
set "ROOT=%~dp0..\.."
if "%MCP_PORT%"=="" set "MCP_PORT=9300"

set "PYW="
if exist "%ROOT%\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\.venv\Scripts\pythonw.exe"
if not defined PYW if exist "%ROOT%\mcp_server\.venv\Scripts\pythonw.exe" set "PYW=%ROOT%\mcp_server\.venv\Scripts\pythonw.exe"
if not defined PYW (
  echo [launch_mcp] venv not found under %ROOT% ^(.venv or mcp_server\.venv^) 1>&2
  exit /b 1
)

cd /d "%ROOT%\mcp_server" || exit /b 2
"%PYW%" server.py --host 0.0.0.0 --port %MCP_PORT% >> server.log 2>&1
exit /b 0
