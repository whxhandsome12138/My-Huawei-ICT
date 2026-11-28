# Keep the MCP server, the demo page and the 3300 forwarder alive.
# Registered by install_watchdog.ps1.
# ASCII only on purpose (PowerShell 5.1 + BOM-less UTF-8 = parse errors).
#
# Ports must match what the agent is configured with. Windows re-randomises its
# excluded port ranges after some reboots, so if the log says RESTART FAILED with
# 10013, run:  netsh int ipv4 show excludedportrange protocol=tcp
# and pick three ports outside those ranges (see README).
#
# Two failure modes this guards against (both observed in the field):
#   1. the forwarder (3300) was never part of the watchdog, so when it died the
#      Nexent page answered ERR_CONNECTION_REFUSED until someone noticed;
#   2. every restart left one extra pythonw behind (the parent cmd exited, the
#      orphan kept running). Six pythonw for three ports was the normal state.
#      Remove-Orphans keeps exactly one process per service.

param(
    [string]$RepoRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701,
    [int]$ForwardPort = 3300,
    [string]$ForwardTarget = '192.168.138.128:3000'
)

$ErrorActionPreference = 'SilentlyContinue'
$Here  = $PSScriptRoot
$State = Join-Path $Here 'watchdog.log'

function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Log([string]$msg) { Add-Content $State "$(Now)  $msg" }

function Test-Port([int]$p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

function Get-PortOwner([int]$p) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess }
    return 0
}

function Get-ServiceProcs([string]$pattern) {
    @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$pattern*" })
}

# Keep only the process that actually owns the listening socket (plus its
# ancestors) and kill the rest.
#
# IMPORTANT: two pythonw per service is NORMAL on this venv. Python 3.13 venv
# installs a redirector stub: the outer pythonw re-executes the base interpreter,
# the inner one is the real process and it is the one that binds the port.
# So the healthy shape is a parent/child pair, not one process. Anything outside
# the owner's ancestor chain is a leftover from an earlier restart.
function Remove-Orphans([int]$port, [string]$pattern) {
    $procs = Get-ServiceProcs $pattern
    if ($procs.Count -le 2) { return }
    $owner = Get-PortOwner $port
    $keep = @()
    if ($owner -gt 0) {
        $keep += $owner
        $cur = $procs | Where-Object { $_.ProcessId -eq $owner } | Select-Object -First 1
        while ($cur) {
            $par = $procs | Where-Object { $_.ProcessId -eq $cur.ParentProcessId } | Select-Object -First 1
            if (-not $par) { break }
            $keep += $par.ProcessId
            $cur = $par
        }
    }
    $killed = 0
    foreach ($p in $procs) {
        if ($keep -contains $p.ProcessId) { continue }
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
    if ($killed -gt 0) {
        Log ("dedupe {0}: killed {1}, kept {2}" -f $pattern, $killed, ($keep -join ','))
    }
}

# $port    : the listening port to wait for
# $bat     : launcher .bat (passes its own args through to the python script)
# $label   : short tag used in the log
# $pattern : substring identifying the python process in its CommandLine
# $batArgs : argument string handed to the .bat
function Ensure([int]$port, [string]$bat, [string]$label, [string]$pattern, [string]$batArgs) {
    Remove-Orphans $port $pattern
    if (Test-Port $port) { return }

    # A process exists but the port is not listening yet: give it a few seconds
    # instead of starting a second copy (that race is how duplicates were born).
    if ((Get-ServiceProcs $pattern).Count -gt 0) {
        for ($w = 0; $w -lt 6; $w++) {
            Start-Sleep -Milliseconds 500
            if (Test-Port $port) { return }
        }
        Remove-Orphans $port $pattern
    }

    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Log ("{0} : port {1} down -> restart (try {2})" -f $label, $port, $attempt)
        $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
            CommandLine = "cmd.exe /c `"$bat`" $batArgs"
        }
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Milliseconds 500
            if (Test-Port $port) {
                Log ("{0} : up (rc={1})" -f $label, $r.ReturnValue)
                return
            }
        }
        Log ("{0} : RESTART FAILED rc={1}" -f $label, $r.ReturnValue)
        Remove-Orphans $port $pattern
        Start-Sleep -Seconds 2
    }
}

Ensure $McpPort     (Join-Path $Here 'launch_mcp.bat')     'mcp    ' 'server.py'     "$McpPort"
Ensure $DemoPort    (Join-Path $Here 'launch_demo.bat')    'demo   ' 'demo\serve.py' "$DemoPort"
Ensure $ForwardPort (Join-Path $Here 'launch_forward.bat') 'forward' 'forward.py'   "--listen-port $ForwardPort --target $ForwardTarget"
