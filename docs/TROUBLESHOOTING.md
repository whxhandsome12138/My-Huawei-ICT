# 排障

按「现象 → 先查什么 → 怎么修」排。每条都是真踩过的。

---

## 1. `ImportError: cannot import name 'FastMCP' from 'mcp.server.fastmcp'`

**原因**：`pip install mcp` 装了 2.x，类改名为 `MCPServer`。

```bash
pip install -U "mcp==1.30.0"
python -c "from mcp.server.fastmcp import FastMCP; print('ok')"
```

---

## 2. Nexent 里 MCP 卡片一直「未连接」

**这是正常的**。SSE 是按需建会话，不开对话就不会连。

想确认真的通：卡片右上角 **⟳** 重新校验；服务端日志应出现 `GET /sse 200` 和若干次 `POST /messages`。

---

## 3. `Run Agent Error: unhandled errors in a TaskGroup (1 sub-exception)`

**这句话没有信息量**，是 anyio 任务组的兜底。它几乎总是意味着**工具服务没在跑**。

```powershell
Get-NetTCPConnection -LocalPort 9100 -State Listen    # 空 = 服务死了
python mcp_server/selfcheck.py --port 9100            # 17/17 才算活
```

最常见的死因：用 `Start-Process` 起的进程挂在启动它的 shell 进程树下，**命令一结束就被回收**。
改用 WMI 起（脱离进程树）：

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd.exe /c cd /d "F:\path\to\mcp_server" && python server.py --host 0.0.0.0 --port 9100 > server.log 2>&1'
}
```

仓库里的 `mcp_server/start.ps1` 已经是这个写法，重启机器后跑一次即可。

---

## 4. 评测得分极低（比如 0.14），但只有「内容安全性」不为 0

**判断**：服务在评测开始前就死了。空答案＝没有不安全内容＝安全性满分，其余全 0。

三件事：

1. 评测前先 `selfcheck.py`，不过别开跑。
2. 评测器别贪多——5 个评估器会把一个问题算成 5 个 0，先只勾「答案准确性 + 回答完整性」。
3. 跑完点开第一条用例，确认回答里真出现了数字（如 `20.901 / 37.489 / −4.068`）。

---

## 5. 模型说「没有返回该指标」，但你在原始 JSON 里看到了

**先信 JSON，再怀疑模型**。这个项目踩过两次：

- `explain_deviation` 的证据在 `data.evidence[]`，不在 `data.deviations[]`（后者只在 `assess_exercise`）。
- 某个指标只出现在 `plan_session` 的记录里，`assess_exercise` 的 fixture 没给——是**我们自己漏了**，不是模型编的。

排查顺序：工具原始返回 → 我们的 fixture → 模型。**不要一上来就说模型幻觉。**

---

## 6. 计算机重启后 / 换机器，工具全挂

两件事要做：

```powershell
# ① 起 MCP（幂等，端口占了就跳过）
powershell -ExecutionPolicy Bypass -File mcp_server\start.ps1

# ② 起 Nexent 虚拟机（如果它跑在 VM 里）
vmrun -T ws start "F:\ubuntu20\ubuntu20\ubuntu20\itop-rk3588.vmx" nogui
```

Nexent 在虚拟机里时，MCP 地址要写**宿主机在虚拟机网段的 IP**（VMware NAT 通常是 `192.168.138.1`），
写 `127.0.0.1` 指向的是虚拟机自己。

> 虚拟机千万别用「挂起 / 恢复」，恢复常报 `[msg.checkpoint.restore.cpufail]`，只能关机重启。

---

## 7. `.bat` 双击闪退，没有任何输出

**行尾必须是 CRLF**。纯 LF 的 bat 在 cmd 下会静默失败（退出码 255）。

```powershell
python tools/fix_bat_crlf.py --check     # 只查
python tools/fix_bat_crlf.py             # 批量修
```

---

## 8. PowerShell 5.1 报 `.ps1` 语法错误，但文件看着没问题

无 BOM 的 UTF-8 中文脚本会被按 GBK 解码，于是 `}` 和引号全乱。

```powershell
python tools/ensure_ps1_bom.py
```

---

## 9. 端口占用

| 端口 | 谁在用 |
| :-- | :-- |
| 3000 | Nexent Web |
| 5010/5011/5012/5013/5014/5015 | Nexent 各服务 |
| 9100 | 本仓库 MCP（默认） |
| 9101 | 演示页 `serve.py` |

改端口：`python server.py --port 9110`，然后 **Nexent 里的 URL 也要跟着改**，改完点 ⟳ 复验。

---

## 10. 绑定 9100 报 `[winerror 10013]`

现象：`server.py --port 9100` 起不来，日志里是

```
ERROR: [Errno 13] error while attempting to bind on address ('0.0.0.0', 9100):
[winerror 10013] 以一种访问权限不允许的方式做了一个访问套接字的尝试。
```

不是权限问题，是 **Windows 把这段端口保留了**（Hyper-V / WSL / Docker Desktop 开启后会占走大段端口）。
先看一眼：

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

如果 9100 落在某个区间里，换个区间外的端口即可（本机部署实际用的是 **9300**）：

```powershell
python server.py --host 0.0.0.0 --port 9300
python selfcheck.py --port 9300
```

---

## 11. `/sse` 返回 502 Bad Gateway（本机自检失败，但 curl 正常）

现象：`curl http://127.0.0.1:9300/sse` 能拿到 `event: endpoint`，但 `selfcheck.py` 抛

```
httpx.HTTPStatusError: Server error '502 Bad Gateway' for url 'http://127.0.0.1:9300/sse'
```

原因是机器上开着系统代理（Clash / 公司代理，WinINET 里 `ProxyEnable=1`），
httpx 会**读代理设置并把回环请求也转给代理**，代理不认识这个目标，回 502。

`selfcheck.py` 已内置兜底（自动把 `127.0.0.1` / `localhost` 加进 `NO_PROXY`）。
如果自己写的客户端也遇到，手动加一句：

```powershell
$env:NO_PROXY = "127.0.0.1,localhost"
```

不用关代理，也不影响别的程序。
