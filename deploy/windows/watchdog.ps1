# Keep the MCP server (and demo page) alive. Meant for Task Scheduler, every 5 minutes.
# ASCII only on purpose (PowerShell 5.1 + BOM-less UTF-8 = parse errors).
#
#   schtasks /Create /SC MINUTE /MO 5 /TN "LiaoyuYoufangWatchdog" ^
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"<repo>\deploy\windows\watchdog.ps1\"" /F
#
# Note: /SC ONLOGON may be refused without admin rights; /SC MINUTE works for normal users.

param(
    [string]$RepoRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [int]$McpPort = 9300,
    [int]$DemoPort = 9301
)

$ErrorActionPreference = 'SilentlyContinue'
$Here  = $PSScriptRoot
$State = Join-Path $Here 'watchdog.log'

function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Test-Port([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

function Ensure([int]$port, [string]$bat, [string]$label) {
    if (Test-Port $port) { return }
    Add-Content $State "$(Now)  $label : port $port down -> restart"
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$bat`"" }
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Port $port) { Add-Content $State "$(Now)  $label : up (rc=$($r.ReturnValue))"; return }
    }
    Add-Content $State "$(Now)  $label : RESTART FAILED rc=$($r.ReturnValue)"
}

Ensure $McpPort  (Join-Path $Here 'launch_mcp.bat')  'mcp '
Ensure $DemoPort (Join-Path $Here 'launch_demo.bat') 'demo'
