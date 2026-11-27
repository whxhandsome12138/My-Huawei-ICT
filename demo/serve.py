# -*- coding: utf-8 -*-
"""把演示页发布成一个可分享的链接（零依赖静态服务）。

用法：
    python serve.py                 # 默认 9701 端口，自动打开浏览器
    python serve.py --port 8080 --no-browser

别人只要在浏览器里打开打印出来的地址即可，不需要装任何东西。
无控制台启动（pythonw）时不会因为 print 到 None 而崩，日志静默丢弃。

端口说明：Windows 上 3000 / 9100 常被 Hyper-V 或 VMware 的保留段占掉
（`netsh int ipv4 show excludedportrange protocol=tcp` 可查），所以默认用 9701。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
HAS_CONSOLE = sys.stdout is not None


def say(msg: str = "") -> None:
    if HAS_CONSOLE:
        print(msg)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 演示页内容会随数据更新，别让浏览器缓存旧版
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if sys.stderr is not None:
            sys.stderr.write("  %s\n" % (fmt % args))


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9701)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(os.path.join(HERE, "index.html")):
        sys.exit("index.html 不存在，先运行 python build_demo.py")

    handler = functools.partial(Handler, directory=HERE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((args.host, args.port), handler) as httpd:
        local = f"http://127.0.0.1:{args.port}/"
        say("\n  聊愈有方 · 动作评估（回放演示）")
        say("  " + "-" * 46)
        say(f"  本机：   {local}")
        for ip in lan_ips():
            say(f"  局域网： http://{ip}:{args.port}/")
        say("  " + "-" * 46)
        say("  同一 Wi-Fi 下的人打开局域网地址即可；Ctrl+C 停止。\n")

        if not args.no_browser and HAS_CONSOLE:
            threading.Timer(0.8, lambda: webbrowser.open(local)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            say("\n  已停止。")


if __name__ == "__main__":
    main()
