# Windows 一键部署脚本（可选）

这套脚本解决的是「在一台 Windows 机器上把演示环境跑起来，并且挂了能自己回来」。
不是必需组件——如果你只用 Docker 或云服务器，看 [`deploy/README.md`](../README.md) 就行。

## 文件

| 文件 | 干什么 |
| :-- | :-- |
| `boot.ps1` | 开机后一次把环境拉起来：MCP 服务 + 演示页 + （可选）内网转发 |
| `watchdog.ps1` | 每 5 分钟检查端口，掉了就重启；配 `schtasks` 用 |
| `launch_mcp.bat` | 起 MCP 服务（`mcp_server/server.py`） |
| `launch_demo.bat` | 起静态演示页（`demo/serve_demo.py`，端口 9301） |
| `launch_forward.bat` | TCP 转发，把宿主某个端口映射到别处（默认可不启用） |
| `check_b.py` | 三层探测任意一个 MCP-over-SSE 端点（端口 / 握手 / 契约） |

## 快速用

```powershell
# 1) 装依赖
python -m venv .venv
.venv\Scripts\pip install -r ..\..\mcp_server\requirements.txt

# 2) 起来一次
powershell -NoProfile -ExecutionPolicy Bypass -File boot.ps1 -RepoRoot "D:\code\My-Huawei-ICT"

# 3) 挂成计划任务（每 5 分钟自检）
schtasks /Create /SC MINUTE /MO 5 /TN "LiaoyuYoufangWatchdog" ^
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"D:\code\My-Huawei-ICT\deploy\windows\watchdog.ps1\" -RepoRoot \"D:\code\My-Huawei-ICT\"" /F
```

## 四个坑（都踩过，脚本里已经绕开）

1. **端口落在 Windows 保留段**。`netsh int ipv4 show excludedportrange protocol=tcp` 看一眼，
   常见保留段是 `2990-3089`、`9022-9121`——所以这里默认用 **9300/9301/3300**，不要用 3000、9100。
   症状是 `OSError: [Errno 13] ... [winerror 10013]`。
2. **`Start-Process` 起的子进程活不长**。用 WMI 创建进程，或者走 `.bat` 包装：
   `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "cmd.exe /c `"$bat`"" }`。
3. **别在 WMI 命令行里写 `cd /d "x" && python ...`**。引号会被吞，python 退化成交互式 REPL：
   进程活着、端口不开、日志里刷 `_pyrepl` traceback。一律写进 `.bat`（CRLF 行尾、纯 ASCII）。
4. **系统代理会劫持回环请求**。开着代理（如 `127.0.0.1:7897`）时，`httpx` 访问 `127.0.0.1:9300/sse`
   会得到 `502 Bad Gateway`，而 `curl` 正常。`selfcheck.py` 和 `check_b.py` 已自动把回环加进 `NO_PROXY`。

## 校验

```powershell
python ..\..\mcp_server\selfcheck.py --port 9300     # 期望 17/17 PASS
python check_b.py 192.168.1.23 8001                  # 测别人机器上的服务
```
