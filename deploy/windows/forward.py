# -*- coding: utf-8 -*-
"""TCP 端口转发：把本机端口原样搬到另一台机器（常用于「宿主机 → 虚拟机里的 Nexent」）。

为什么是 TCP 层而不是 HTTP 反代：
    Nexent 的对话是流式（SSE / WebSocket）。HTTP 反代若只处理普通请求会断流；
    这里只搬字节、不解析协议，所以流式、长连接、上传下载都不会坏。

用法：
    python forward.py --target 192.168.1.50:3000              # 0.0.0.0:3300 -> 192.168.1.50:3000
    python forward.py --target 192.168.1.50:3000 --listen-port 8080
    python forward.py --target 192.168.1.50:3000 --check      # 只探测目标是否可达
"""
from __future__ import annotations

import argparse
import socket
import socketserver
import sys
import threading
import time

BUFSIZE = 65536

# Windows 控制台默认 GBK，输出里带非 GBK 字符会直接抛异常
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def lan_ips() -> list[str]:
    ips: set[str] = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith("127."))


def check(target: tuple[str, int], timeout: float = 4.0) -> bool:
    log(f"探测 {target[0]}:{target[1]} ...")
    try:
        with socket.create_connection(target, timeout=timeout):
            log("目标可达 [OK]")
            return True
    except OSError as e:
        log(f"目标不可达 [FAIL] {e}")
        return False


class Proxy(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        src = self.request.getpeername()
        peer = f"{src[0]}:{src[1]}"
        target = self.server.target  # type: ignore[attr-defined]
        try:
            remote = socket.create_connection(target, timeout=10)
        except OSError as e:
            log(f"{peer} 连不上后端 {target[0]}:{target[1]}：{e}")
            self.request.close()
            return
        log(f"{peer} -> {target[0]}:{target[1]}")

        def pipe(a: socket.socket, b: socket.socket) -> None:
            try:
                while True:
                    data = a.recv(BUFSIZE)
                    if not data:
                        break
                    b.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    b.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        t = threading.Thread(target=pipe, args=(remote, self.request), daemon=True)
        t.start()
        pipe(self.request, remote)
        t.join(timeout=5)
        remote.close()
        self.request.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="0.0.0.0")
    ap.add_argument("--listen-port", type=int, default=3300)
    ap.add_argument("--target", default="192.168.138.128:3000", help="host:port")
    ap.add_argument("--check", action="store_true", help="只探测目标，不启动监听")
    args = ap.parse_args()

    host, _, port = args.target.rpartition(":")
    target = (host, int(port))

    if args.check:
        sys.exit(0 if check(target) else 1)

    if not check(target):
        log("目标未就绪，先把它启动起来再跑本脚本。")
        sys.exit(1)

    with Server((args.listen_host, args.listen_port), Proxy) as srv:
        srv.target = target  # type: ignore[attr-defined]
        print()
        print("  转发已启动")
        print("  " + "-" * 50)
        print(f"  后端：  {target[0]}:{target[1]}")
        print(f"  本机：  http://127.0.0.1:{args.listen_port}/")
        for ip in lan_ips():
            print(f"  对外：  http://{ip}:{args.listen_port}/")
        print("  " + "-" * 50)
        print("  Ctrl+C 停止。别把管理员账号发给外部人员。")
        print()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  已停止。")


if __name__ == "__main__":
    main()
