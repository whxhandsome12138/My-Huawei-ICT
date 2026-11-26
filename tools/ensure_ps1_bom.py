# -*- coding: utf-8 -*-
"""给 .ps1 补 UTF-8 BOM（Windows PowerShell 5.1 没 BOM 会把中文读成乱码并报语法错）。

用法：
    python ensure_ps1_bom.py <目录或文件> [...]
    python ensure_ps1_bom.py --check <目录>
"""
from __future__ import annotations

import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"


def targets(p: Path):
    if p.is_file() and p.suffix.lower() == ".ps1":
        yield p
    elif p.is_dir():
        for f in sorted(p.rglob("*.ps1")):
            if f.is_file():
                yield f


def main() -> None:
    args = sys.argv[1:]
    dry = "--check" in args
    args = [a for a in args if a != "--check"]
    if not args:
        print(__doc__)
        sys.exit(2)

    for a in args:
        for f in targets(Path(a)):
            raw = f.read_bytes()
            if raw.startswith(BOM):
                continue
            if dry:
                print(f"needs BOM: {f}")
            else:
                f.write_bytes(BOM + raw)
                print(f"added BOM: {f}")


if __name__ == "__main__":
    main()
