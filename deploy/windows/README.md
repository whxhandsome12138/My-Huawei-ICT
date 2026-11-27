# Windows 一键部署脚本（可选）

这套脚本解决的是「在一台 Windows 机器上把演示环境跑起来，并且挂了能自己回来」。
不是必需组件——如果你只用 Docker 或云服务器，看 [`deploy/README.md`](../README.md) 就行。

## 文件

| 文件 | 干什么 |
| :-- | :-- |
| `start_all.ps1` | **一键全起**：启用看门狗 → 起虚拟机等 Nexent 就绪 → 起 MCP/演示页 → 起 3300 转发 |
| `stop_all.ps1` | **一键全停**：先停看门狗（否则 5 分钟又被拉起）→ 关 3300/9701/9700 → 正常关机虚拟机 |
| `watchdog_hidden.vbs` | 看门狗任务的启动器，用 `wscript.exe` 调 `watchdog.ps1`，**不建控制台**（见下文「弹窗」） |
| `boot.ps1` | 开机后一次把环境拉起来：MCP 服务 + 演示页 + （可选）内网转发 |
| `watchdog.ps1` | 每 5 分钟检查端口，掉了就重启；由 `install_watchdog.ps1` 注册 |
| `install_watchdog.ps1` | 注册 / 卸载那个 5 分钟任务，不需要管理员权限 |
| `launch_mcp.bat` | 起 MCP 服务（`mcp_server/server.py`） |
| `launch_demo.bat` | 起静态演示页（`demo/serve.py`，端口 9701） |
| `launch_forward.bat` | TCP 转发，把宿主某个端口映射到别处（默认可不启用） |
| `check_b.py` | 三层探测任意一个 MCP-over-SSE 端点（端口 / 握手 / 契约） |

## 快速用

```powershell
# 1) 装依赖
python -m venv .venv
.venv\Scripts\pip install -r ..\..\mcp_server\requirements.txt

# 2) 起来一次
powershell -NoProfile -ExecutionPolicy Bypass -File boot.ps1 -RepoRoot "D:\code\My-Huawei-ICT"

# 3) 挂成计划任务（每 5 分钟自检 9700/9701）
powershell -NoProfile -ExecutionPolicy Bypass -File install_watchdog.ps1

# 不想要了
powershell -NoProfile -ExecutionPolicy Bypass -File install_watchdog.ps1 -Uninstall
```

## 开机自启：默认不装

**这套脚本不会把自己挂到开机启动里**，虚拟机也不会。装了什么、在哪，一眼看得见：

| 想要的效果 | 怎么做 |
| :-- | :-- |
| 只保活 MCP + 演示页（推荐） | `install_watchdog.ps1`，任务名 `LiaoyuYoufangWatchdog`，5 分钟一次 |
| 开机连虚拟机一起起来 | 自己在「启动」文件夹放一个 `.vbs` 调 `boot.ps1 -Vmx <vmx路径>`——**需要 VM 时才加 `-Vmx`**，不加就只起本机服务 |
| 什么都不自动 | 什么都不装，要用时手动跑 `boot.ps1` |

`boot.ps1` 只有给了 `-Vmx` 才会调 `vmrun`；没给就只处理本机进程。想彻底关掉某台机器的自启，检查三处：
`shell:startup` 文件夹、`schtasks /Query` 里带项目名的任务、`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`。

## 为什么以前会莫名弹一个 PowerShell 黑窗

计划任务原来把 `powershell.exe` 直接当 action。Task Scheduler 在交互会话里启动进程时，**会先给它分配一个控制台**，
`-WindowStyle Hidden` 只隐藏窗口，控制台本身仍会被创建 → 每 5 分钟屏幕上闪一下黑框。

修法是让任务去调 `wscript.exe` + `watchdog_hidden.vbs`，由 VBS 用 `WScript.Shell.Run(cmd, 0, False)` 起 PowerShell：
`0` = 完全不建控制台，`False` = 不等待。这样任务照常每 5 分钟跑，但屏幕上什么都看不到。

```powershell
# 确认动作已经不是 powershell.exe
(Get-ScheduledTask -TaskName 'LiaoyuYoufangWatchdog').Actions | Format-List Execute, Arguments
# 期望 Execute: wscript.exe
```

## 四个坑（都踩过，脚本里已经绕开）

1. **端口落在 Windows 保留段**。`netsh int ipv4 show excludedportrange protocol=tcp` 看一眼，
   保留段**每次开机都可能变**（Hyper-V / WSL / Docker 会重新占），先查再定端口，别背数字。
   本机就遇到过：早先 `9022-9121`，后来变成 `9161-9260`、`9261-9360`，把 9300/9301 吃了，
   才改成现在的 **9700/9701**（转发用 3300）。症状是 `OSError: [Errno 13] ... [winerror 10013]`，
   兜底手段：`net stop winnat` + `net start winnat` 可以清掉一段动态保留，但不建议长期这么干。
2. **`Start-Process` 起的子进程活不长**。用 WMI 创建进程，或者走 `.bat` 包装：
   `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$bat`"" }`。
3. **别在 WMI 命令行里写 `cd /d "x" && python ...`**。引号会被吞，python 退化成交互式 REPL：
   进程活着、端口不开、日志里刷 `_pyrepl` traceback。一律写进 `.bat`（CRLF 行尾、纯 ASCII）。
4. **系统代理会劫持回环请求**。开着代理（如 `127.0.0.1:7897`）时，`httpx` 访问 `127.0.0.1:9700/sse`
   会得到 `502 Bad Gateway`，而 `curl` 正常。`selfcheck.py` 和 `check_b.py` 已自动把回环加进 `NO_PROXY`。

## 校验

```powershell
python ..\..\mcp_server\selfcheck.py --port 9700     # 期望 17/17 PASS
python check_b.py 192.168.1.23 8001                  # 测别人机器上的服务
```
