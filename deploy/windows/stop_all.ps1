# 聊愈有方 · 一键停止（本机部分）
#   - 先停掉看门狗任务（否则它 5 分钟内又会把服务拉起来）
#   - 关掉 3300 转发、9701 演示页、9700 MCP
#   - 正常关机虚拟机（soft），超时再强关
#
# 用 停止Nexent.bat 调它就行。参数：-KeepVm 只停本机服务，虚拟机留着自己关。

param(
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701,
    [int]$ForwardPort = 3300,
    [switch]$KeepVm
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Here    = $PSScriptRoot
$LogFile = Join-Path $Here 'stop_all.log'
$Vmrun   = 'F:\VMware\vmrun.exe'
$Vmx     = 'F:\ubuntu20\ubuntu20\ubuntu20\itop-rk3588.vmx'
$TaskName = 'LiaoyuYoufangWatchdog'

function Log([string]$msg, [string]$color = 'Gray') {
    $line = '{0}  {1}' -f (Get-Date).ToString('HH:mm:ss'), $msg
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Stop-Listener([int]$port, [string]$label) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { Log ("  {0} ({1}) 本来就没在跑" -f $label, $port) 'DarkGray'; return }
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Log ("  {0} ({1}) 已停，pid {2}" -f $label, $port, $c.OwningProcess) 'Green'
        } catch {
            Log ("  {0} ({1}) 停不掉：{2}" -f $label, $port, $_.Exception.Message) 'Yellow'
        }
    }
}

Log '================ 聊愈有方 一键停止 ================' 'Cyan'

# ---------- 1. 先摘看门狗 ----------
Log '[1/3] 停用看门狗任务（否则 5 分钟后又被拉起来）…'
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    try {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Log '      看门狗已停用' 'Green'
    } catch {
        Log ("      [警告] 停用失败：{0}" -f $_.Exception.Message) 'Yellow'
    }
} else {
    Log '      任务不存在，跳过' 'DarkGray'
}

# ---------- 2. 停本机服务 ----------
Log '[2/3] 关闭本机服务…'
Stop-Listener $ForwardPort '3300 转发'
Stop-Listener $DemoPort    '演示页'
Stop-Listener $McpPort     'MCP 服务'

# ---------- 3. 虚拟机 ----------
if ($KeepVm) {
    Log '[3/3] 保持虚拟机运行（-KeepVm）' 'Yellow'
} else {
    Log '[3/3] 正常关闭虚拟机…'
    $running = (& $Vmrun -T ws list 2>&1) -join "`n"
    if ($running -notmatch [regex]::Escape((Split-Path $Vmx -Leaf))) {
        Log '      虚拟机本来就没开' 'DarkGray'
    } else {
        & $Vmrun -T ws stop $Vmx soft | Out-Null
        $deadline = (Get-Date).AddSeconds(90)
        $stopped = $false
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
            $now = (& $Vmrun -T ws list 2>&1) -join "`n"
            if ($now -notmatch [regex]::Escape((Split-Path $Vmx -Leaf))) { $stopped = $true; break }
        }
        if ($stopped) {
            Log '      已正常关机' 'Green'
        } else {
            Log '      正常关机超时，强制关机…' 'Yellow'
            & $Vmrun -T ws stop $Vmx hard | Out-Null
            Start-Sleep -Seconds 3
            Log '      已强制关机' 'Yellow'
        }
    }
}

Log '------------------------------------------------' 'Cyan'
Log '  已全部停止。下次用「启动Nexent.bat」。' 'White'
Log '  提醒：VMware 里永远不要点「挂起」，恢复会报 cpufail。' 'DarkGray'
Log '================================================' 'Cyan'
