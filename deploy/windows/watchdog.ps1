# Keep the MCP server (and demo page) alive. Registered by install_watchdog.ps1.
# ASCII only on purpose (PowerShell 5.1 + BOM-less UTF-8 = parse errors).
#
# Ports must match what the agent is configured with. Windows re-randomises its
# excluded port ranges after some reboots, so if the log says RESTART FAILED with
# 10013, run:  netsh int ipv4 show excludedportrange protocol=tcp
# and pick three ports outside those ranges (see README).

param(
    [string]$RepoRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701
)

$ErrorActionPreference = 'SilentlyContinue'
$Here  = $PSScriptRoot
$State = Join-Path $Here 'watchdog.log'

function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Test-Port([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

function Ensure([int]$port, [string]$bat, [string]$label) {
    if (Test-Port $port) { return }
    Add-Content $State "$(Now)  $label : port $port down -> restart"
    # The port is passed through to the .bat; the .bat defaults to 9700/9701 otherwise.
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$bat`" $port" }
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Port $port) { Add-Content $State "$(Now)  $label : up (rc=$($r.ReturnValue))"; return }
    }
    Add-Content $State "$(Now)  $label : RESTART FAILED rc=$($r.ReturnValue)"
}

Ensure $McpPort  (Join-Path $Here 'launch_mcp.bat')  'mcp '
Ensure $DemoPort (Join-Path $Here 'launch_demo.bat') 'demo'
