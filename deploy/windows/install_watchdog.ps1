# Register (or remove) the 5-minute watchdog task. ASCII only.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_watchdog.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_watchdog.ps1 -Uninstall
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_watchdog.ps1 -TaskName "MyWatchdog"
#
# What it keeps alive: the MCP server (9700) and the static demo page (9701).
# What it does NOT do: start a VM, start Nexent, or ask for admin rights.
#
# Why this script instead of schtasks:
#   The schtasks /TR string has to survive two layers of quoting (cmd.exe, then
#   Task Scheduler). A stray space or a stripped backslash makes the task fail
#   silently every 5 minutes. New-ScheduledTaskAction passes the argument list
#   through as data, so there is nothing to escape.

param(
    [string]$TaskName = "LiaoyuYoufangWatchdog",
    [string]$ScriptPath = (Join-Path $PSScriptRoot "watchdog.ps1"),
    [int]$McpPort = 9700,
    [int]$DemoPort = 9701,
    [int]$ForwardPort = 3300,
    [string]$ForwardTarget = "192.168.138.128:3000",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

if ($Uninstall) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        "removed: $TaskName"
    } else {
        "not found: $TaskName"
    }
    exit 0
}

if (-not (Test-Path $ScriptPath)) {
    "missing script: $ScriptPath"
    exit 1
}

$vbs = Join-Path $PSScriptRoot "watchdog_hidden.vbs"
if (-not (Test-Path $vbs)) {
    "missing launcher: $vbs"
    exit 1
}

# Run through a VBS launcher: powershell.exe started by Task Scheduler always
# allocates a console first, so -WindowStyle Hidden still flashes a black window
# every 5 minutes. WScript.Shell.Run(cmd, 0, False) creates no console at all.
$arg = '//nologo "{0}" {1} {2} {3} {4}' -f $vbs, $McpPort, $DemoPort, $ForwardPort, $ForwardTarget

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Keep the Liaoyu Youfang MCP server, demo page and 3300 forwarder alive (every 5 min)." `
    -Force | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
"registered: {0}  state={1}" -f $t.TaskName, $t.State
$t.Actions | ForEach-Object {
    "  execute : {0}" -f $_.Execute
    "  argument: {0}" -f $_.Arguments
}
"verify with: schtasks /Query /TN `"$TaskName`" /FO CSV /NH"
