# -*- coding: utf-8 -*-
"""把 .bat / .cmd 的行尾统一成 CRLF（cmd.exe 不认纯 LF，会静默失败）。

背景：用编辑器/生成器写出的 .bat 如果是 LF 行尾，双击后 cmd 会解析错乱——
常见表现是「什么都不输出、退出码 255」，排查起来很费时间。

用法：
    python fix_bat_crlf.py <目录> [<目录> ...]
    python fix_bat_crlf.py --check <目录>     # 只检查，不改
"""
from __future__ import annotations

import sys
from pathlib import Path


def fix(path: Path, dry: bool) -> bool:
    raw = path.read_bytes()
    if b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"):
        return False  # 已经是 CRLF
    fixed = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if not dry:
        path.write_bytes(fixed)
    return True


def main() -> None:
    args = [a for a in sys.argv[1:]]
    dry = "--check" in args
    args = [a for a in args if a != "--check"]
    if not args:
        print(__doc__)
        sys.exit(2)

    total = changed = 0
    for d in args:
        for p in sorted(Path(d).rglob("*")):
            if p.suffix.lower() not in {".bat", ".cmd"} or not p.is_file():
                continue
            total += 1
            if fix(p, dry):
                changed += 1
                print(f"{'would fix' if dry else 'fixed'}: {p}")
    print(f"\n{total} 个批处理文件，{changed} 个需要转换行尾" + ("（未改动）" if dry else "（已转换）"))


if __name__ == "__main__":
    main()
