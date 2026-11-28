"""检查任意一个 MCP-over-SSE 端点能不能用（默认按 8001 端口、也就是评估内核服务的约定）。

三层判定，逐层给结论，不做任何假设：

    第一层  端口通不通      —— TCP 能不能连上（网络 / 防火墙 / 绑定地址）
    第二层  MCP 握手通不通  —— /sse 是否返回 event: endpoint（协议 / 路径对不对）
    第三层  契约对不对      —— 复用 selfcheck.py 的 17 项断言（工具名、字段、数值、错误码）

用法：
    python check_b.py 192.168.1.23                # 默认 8001
    python check_b.py 192.168.1.23 8002           # Streamable HTTP 备用端口
    python check_b.py 192.168.1.23 8001 --quick   # 只跑前两层

退出码：0 全通 / 2 端口不通 / 3 握手不通 / 4 契约不符
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request

# Windows 控制台默认 GBK，中文输出会变乱码；统一按 UTF-8 写，bat 里配合 chcp 65001
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SELFCHECK = os.path.join(REPO, "mcp_server", "selfcheck.py")


def layer1_tcp(host: str, port: int) -> bool:
    print(f"[1/3] TCP {host}:{port} ... ", end="", flush=True)
    try:
        with socket.create_connection((host, port), timeout=5):
            print("OK")
            return True
    except OSError as e:
        print(f"失败：{e}")
        print()
        print("  这一层不通，先别怀疑代码，按顺序查：")
        print("    a) 服务是不是绑在 0.0.0.0 而不是 127.0.0.1（绑回环别人连不上）")
        print("    b) 防火墙有没有放行端口（Windows 上 WinError 10061 多半是防火墙）")
        print("    c) 两端是不是同一个网络（不在同网段就是不通）")
        print(f"    d) 让对方在自己机器上跑：Test-NetConnection 127.0.0.1 -Port {port}")
        return False


def layer2_sse(host: str, port: int) -> bool:
    print(f"[2/3] GET http://{host}:{port}/sse ... ", end="", flush=True)
    # 本机可能开着系统代理，httpx/urllib 会把回环请求也转出去
    for k in ("NO_PROXY", "no_proxy"):
        os.environ[k] = ",".join(filter(None, [os.environ.get(k, ""), "127.0.0.1", "localhost", host]))
    req = urllib.request.Request(
        f"http://{host}:{port}/sse",
        headers={"Accept": "text/event-stream", "Host": f"{host}:{port}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            # SSE 是长连接：不能 read(n) 等满 n 字节（会阻塞到超时），逐行读前几行
            got = []
            for _ in range(6):
                line = r.readline()
                if not line:
                    break
                got.append(line.decode("utf-8", "replace"))
                if "event: endpoint" in "".join(got) or "event:endpoint" in "".join(got):
                    break
        text = "".join(got)
        if "event: endpoint" in text or "event:endpoint" in text:
            print("OK（是 MCP over SSE）")
            return True
        print(f"有响应但不是 MCP SSE：{text[:80]!r}")
        print("  端口上有东西，但不是 MCP 服务（可能是别的网页服务占了这个端口）")
        return False
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        if e.code == 421:
            print("  421 = Host 不在白名单。启动时加 --allowed-host <你的IP或域名>")
        elif e.code == 403:
            print("  403 = Origin 被拒。加 --allowed-origin，或用不带 Origin 的客户端（本脚本就是）")
        else:
            print("  这个端口确实有 HTTP 服务，但不是我们要的 /sse")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"失败：{e}")
        print("  端口通但 /sse 取不到数据：多半是路径不对，或服务只开了 /mcp（Streamable HTTP）")
        print(f"  换个端口再试：python check_b.py {host} 8002")
        return False


def layer3_contract(host: str, port: int) -> bool:
    print("[3/3] 17 项契约断言 ... ")
    if not os.path.exists(SELFCHECK):
        print(f"  跳过：找不到 {SELFCHECK}")
        return False
    cmd = [sys.executable, SELFCHECK, "--host", host, "--port", str(port)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in out.splitlines() if ln.strip()][-6:]
    for ln in tail:
        print("  " + ln)
    ok = p.returncode == 0 and "17/17 PASS" in out
    print("  => " + ("全通，可以切过去了" if ok else "有断言没过，把上面这段发给服务方"))
    return ok


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else ""
    if not host:
        host = input("对方机器 IP（或主机名）：").strip()
    port = 8001
    quick = False
    for a in sys.argv[2:]:
        if a == "--quick":
            quick = True
        elif a.isdigit():
            port = int(a)
    print(f"目标：{host}:{port}\n")
    if not layer1_tcp(host, port):
        return 2
    if not layer2_sse(host, port):
        return 3
    if quick:
        print("\n前两层通了。完整契约检查：去掉 --quick 再跑一次。")
        return 0
    return 0 if layer3_contract(host, port) else 4


if __name__ == "__main__":
    raise SystemExit(main())
