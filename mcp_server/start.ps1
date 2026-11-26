# Start the replay MCP server and run the self-check.
# Usage:  powershell -ExecutionPolicy Bypass -File start.ps1
# Keep this file ASCII-only: PowerShell 5.1 misreads UTF-8 without BOM.

$wd   = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 9100

$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    # Launch detached through WMI: a Start-Process child dies when the calling
    # shell exits, which silently killed the service during an eval run.
    $cmd = "cmd.exe /c cd /d `"$wd`" && python server.py --host 0.0.0.0 --port $port > server.log 2> server.err.log"
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
    if ($r.ReturnValue -ne 0) {
        Write-Host "[fail] WMI launch returned $($r.ReturnValue)"
        exit 1
    }
    Write-Host "[start] launcher pid $($r.ProcessId), waiting..."
    Start-Sleep -Seconds 8
} else {
    Write-Host "[start] already listening on $port"
}

$now = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $now) {
    Write-Host "[fail] port $port is not listening. See server.err.log"
    exit 1
}
Write-Host "[ok] listening on 0.0.0.0:$port  (Nexent URL: http://192.168.138.1:$port/sse)"

Write-Host ""
python "$wd\selfcheck.py" --port $port
