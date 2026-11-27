# 聊愈有方 · 一键启动（本机部分）
#   - 确保看门狗计划任务处于启用状态（每 5 分钟保活 9700/9701）
#   - 起虚拟机并等 Nexent(3000) 就绪
#   - 起 MCP 服务(9700) + 演示页(9701)
#   - 起 3300 转发（Nexent 的 3000 映射到宿主 3300，方便别人访问）
#
# 用 启动Nexent.bat 调它就行，一般不用直接跑。
# 参数：-SkipVm 只起本机服务（虚拟机自己开）；-NoBrowser 不自动开浏览器。

param(
    [switch]$SkipVm,
    [switch]$NoBrowser,
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701,
    [int]$ForwardPort = 3300
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Here    = $PSScriptRoot
# 兼容两种放法：放在 <test>\ 下（仓库在子目录 My-Huawei-ICT），或直接放在 <repo>\deploy\windows\ 里。
function Resolve-Repo([string]$start) {
    $cands = @(
        (Join-Path $start 'My-Huawei-ICT'),
        (Split-Path (Split-Path $start -Parent) -Parent),
        $start
    )
    foreach ($c in $cands) {
        if ($c -and (Test-Path (Join-Path $c 'mcp_server'))) { return $c }
    }
    return $start
}
$Repo    = Resolve-Repo $Here
$WinDir  = Join-Path $Repo 'deploy\windows'
$LogFile = Join-Path $Here 'start_all.log'
$Vmrun   = 'F:\VMware\vmrun.exe'
$Vmx     = 'F:\ubuntu20\ubuntu20\ubuntu20\itop-rk3588.vmx'
$Guest   = '192.168.138.128'
$GuestPort = 3000
$TaskName = 'LiaoyuYoufangWatchdog'

function Log([string]$msg, [string]$color = 'Gray') {
    $line = '{0}  {1}' -f (Get-Date).ToString('HH:mm:ss'), $msg
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Test-Port([string]$host_, [int]$port) {
    try {
        $c = New-Object Net.Sockets.TcpClient
        $t = $c.ConnectAsync($host_, $port)
        if ($t.Wait(1500) -and $c.Connected) { $c.Close(); return $true }
        $c.Close()
    } catch {}
    return $false
}

function Wait-Port([string]$host_, [int]$port, [int]$seconds, [string]$label) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $host_ $port) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Stop-Listener([int]$port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Log ("  stopped pid {0} on {1}" -f $c.OwningProcess, $port) } catch {}
    }
}

Log '================ 聊愈有方 一键启动 ================' 'Cyan'

# ---------- 0. 前置检查 ----------
foreach ($p in @($Vmrun, $Vmx, $WinDir)) {
    if (-not (Test-Path $p)) { Log "[错误] 找不到：$p" 'Red'; exit 1 }
}

# ---------- 1. 看门狗任务 ----------
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Log '[1/4] 注册看门狗任务…'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WinDir 'install_watchdog.ps1') `
        -ScriptPath (Join-Path $WinDir 'watchdog.ps1') -McpPort $McpPort -DemoPort $DemoPort | Out-Null
} else {
    if ($task.State -eq 'Disabled') {
        Enable-ScheduledTask -TaskName $TaskName | Out-Null
        Log '[1/4] 看门狗任务已重新启用'
    } else {
        Log '[1/4] 看门狗任务已存在且启用'
    }
}

# ---------- 2. 虚拟机 + Nexent ----------
if ($SkipVm) {
    Log '[2/4] 跳过虚拟机（-SkipVm）' 'Yellow'
} else {
    $running = (& $Vmrun -T ws list 2>&1) -join "`n"
    if ($running -match [regex]::Escape((Split-Path $Vmx -Leaf))) {
        Log '[2/4] 虚拟机已在运行'
    } else {
        Log '[2/4] 冷启动虚拟机（不要用「挂起」，恢复会报 cpufail）…'
        & $Vmrun -T ws start $Vmx nogui | Out-Null
    }
    Log ("      等待 Nexent {0}:{1} 就绪（最长 300 秒）…" -f $Guest, $GuestPort)
    if (Wait-Port $Guest $GuestPort 300 'nexent') {
        Log '      Nexent 已就绪' 'Green'
    } else {
        Log '      [警告] 300 秒内没起来，进虚拟机看 docker ps' 'Yellow'
    }
}

# ---------- 3. MCP + 演示页 ----------
Log '[3/4] 检查 MCP / 演示页…'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WinDir 'watchdog.ps1') `
    -McpPort $McpPort -DemoPort $DemoPort | Out-Null
Start-Sleep -Seconds 3
$mcpOk  = Test-Port '127.0.0.1' $McpPort
$demoOk = Test-Port '127.0.0.1' $DemoPort
Log ("      MCP {0}: {1}" -f $McpPort, $(if ($mcpOk) { 'OK' } else { '未起来' })) $(if ($mcpOk) { 'Green' } else { 'Red' })
Log ("      演示页 {0}: {1}" -f $DemoPort, $(if ($demoOk) { 'OK' } else { '未起来' })) $(if ($demoOk) { 'Green' } else { 'Red' })

# ---------- 4. 3300 转发 ----------
Log '[4/4] 检查 3300 转发…'
if (Test-Port '127.0.0.1' $ForwardPort) {
    Log ("      转发 {0} 已在监听" -f $ForwardPort) 'Green'
} else {
    $bat = Join-Path $WinDir 'launch_forward.bat'
    if (Test-Path $bat) {
        Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$bat`"" } | Out-Null
        if (Wait-Port '127.0.0.1' $ForwardPort 20 'forward') {
            Log ("      转发 {0} 已启动" -f $ForwardPort) 'Green'
        } else {
            Log ("      [警告] 转发 {0} 没起来（虚拟机没开时属正常）" -f $ForwardPort) 'Yellow'
        }
    } else {
        Log "      [警告] 缺少 $bat" 'Yellow'
    }
}

# ---------- 小结 ----------
$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } |
       Select-Object -ExpandProperty IPAddress
Log '------------------------------------------------' 'Cyan'
Log ("  Nexent      : http://{0}:{1}" -f $Guest, $GuestPort) 'White'
Log ("  Nexent 转发 : http://127.0.0.1:{0}" -f $ForwardPort) 'White'
Log ("  MCP (SSE)   : http://127.0.0.1:{0}/sse" -f $McpPort) 'White'
Log ("  演示页      : http://127.0.0.1:{0}/" -f $DemoPort) 'White'
Log ("  本机地址    : {0}" -f ($ips -join '  ')) 'DarkGray'
Log '  停止全部：运行「停止Nexent.bat」' 'DarkGray'
Log '================================================' 'Cyan'

if (-not $NoBrowser) {
    Start-Process ("http://{0}:{1}" -f $Guest, $GuestPort)
}
