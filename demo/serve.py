# -*- coding: utf-8 -*-
"""把演示页发布成一个可分享的链接。

用法：
    python serve.py            # 默认 9101 端口，自动打开浏览器
    python serve.py --port 9200

别人只要在浏览器里打开打印出来的地址即可，不需要装任何东西。
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


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 安静一点，只打关键行
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
    ap.add_argument("--port", type=int, default=9101)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(os.path.join(HERE, "index.html")):
        sys.exit("index.html 不存在，先运行 python build_demo.py")

    handler = functools.partial(Handler, directory=HERE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((args.host, args.port), handler) as httpd:
        local = f"http://127.0.0.1:{args.port}/"
        print("\n  聊愈有方 · 动作评估（回放演示）")
        print("  " + "-" * 46)
        print(f"  本机：   {local}")
        for ip in lan_ips():
            print(f"  局域网： http://{ip}:{args.port}/")
        print("  " + "-" * 46)
        print("  同一 Wi-Fi 下的人打开局域网地址即可；Ctrl+C 停止。\n")

        if not args.no_browser:
            threading.Timer(0.8, lambda: webbrowser.open(local)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  已停止。")


if __name__ == "__main__":
    main()
