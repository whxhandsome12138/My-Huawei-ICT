# Bring the whole demo stack up on Windows: MCP server + static demo page (+ optional TCP forward).
# ASCII only on purpose: PowerShell 5.1 mis-parses UTF-8 .ps1 files without a BOM.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File boot.ps1 -RepoRoot "D:\code\My-Huawei-ICT"
#   powershell -NoProfile -ExecutionPolicy Bypass -File boot.ps1 -Vmx "D:\vm\nexent.vmx" -ForwardPort 3300 -ForwardTarget 192.168.1.50:3000

param(
    [string]$RepoRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701,
    [int]$ForwardPort = 0,
    [string]$ForwardTarget = "",
    [string]$Vmx = "",
    [string]$Vmrun = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
)

$ErrorActionPreference = 'SilentlyContinue'
$Here = $PSScriptRoot
$Log  = Join-Path $Here 'boot.log'

function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Log($m) { Add-Content $Log "$(Now)  $m" }
function Test-Port([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
function Start-Bat([string]$path) {
    if (-not (Test-Path $path)) { return -1 }
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$path`"" }
    return $r.ReturnValue
}

Log '=== boot start ==='

# 0) optional: start a VM that hosts Nexent or the data
if ($Vmx -and (Test-Path $Vmx)) {
    $running = & $Vmrun list 2>$null | Select-String -SimpleMatch $Vmx
    if (-not $running) {
        Log "vmrun start $Vmx"
        & $Vmrun -T ws start $Vmx nogui | Out-Null
        Start-Sleep -Seconds 10
    } else {
        Log 'vm already running'
    }
}

# 1) MCP server
if (Test-Port $McpPort) {
    Log "mcp already listening on $McpPort"
} else {
    $rc = Start-Bat (Join-Path $Here 'launch_mcp.bat')
    for ($i = 0; $i -lt 30; $i++) { Start-Sleep -Milliseconds 500; if (Test-Port $McpPort) { break } }
    Log ("mcp start rc={0} listening={1}" -f $rc, (Test-Port $McpPort))
}

# 2) demo page
if (Test-Port $DemoPort) {
    Log "demo already listening on $DemoPort"
} else {
    $rc = Start-Bat (Join-Path $Here 'launch_demo.bat')
    for ($i = 0; $i -lt 20; $i++) { Start-Sleep -Milliseconds 500; if (Test-Port $DemoPort) { break } }
    Log ("demo start rc={0} listening={1}" -f $rc, (Test-Port $DemoPort))
}

# 3) optional TCP forward
if ($ForwardPort -gt 0) {
    if (Test-Port $ForwardPort) {
        Log "forward already listening on $ForwardPort"
    } elseif ($ForwardTarget) {
        $env:FWD_LISTEN = "$ForwardPort"
        $env:FWD_TARGET = $ForwardTarget
        $rc = Start-Bat (Join-Path $Here 'launch_forward.bat')
        Start-Sleep -Seconds 2
        Log ("forward start rc={0} listening={1}" -f $rc, (Test-Port $ForwardPort))
    }
}

# 4) summary
$ips = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -ExpandProperty IPAddress)
Log ("final: mcp={0} demo={1} forward={2}" -f (Test-Port $McpPort), (Test-Port $DemoPort), (Test-Port $ForwardPort))
Log '=== boot done ==='
Write-Host ("mcp http://127.0.0.1:{0}/sse   demo http://127.0.0.1:{1}/" -f $McpPort, $DemoPort)
foreach ($ip in $ips) { Write-Host ("  LAN: http://{0}:{1}/" -f $ip, $DemoPort) }
