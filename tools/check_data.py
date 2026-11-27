"""校验本地是否有可用的 KIMORE 数据副本。

数据集不进仓库（3.5 GB + 第三方许可），所以「有没有数据」这件事得靠校验清单确认。
这个脚本读 `data/SHA256SUMS.txt`，在给定目录里按文件名找，逐条报：

    通过 / 缺失 / 大小不符 / 哈希不符

用法：

    python tools/check_data.py --root E:/study/3u/ICT/reference
    python tools/check_data.py --root ./data --no-hash     # 只比大小（快）

退出码：0 = 四个文件全通过；1 = 有缺失或校验失败。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMS = ROOT / "data" / "SHA256SUMS.txt"

try:  # Windows 控制台默认 GBK，中文提示会乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_sums(path: Path) -> list[tuple[str, str, int, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        digest, name, size = parts[0], parts[1], int(parts[2])
        note = " ".join(parts[3:])
        rows.append((digest, name, size, note))
    return rows


def sha256_file(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="校验 KIMORE 数据副本")
    ap.add_argument("--root", default=str(Path.home() / "KIMORE"),
                    help="放 zip / pdf 的目录（默认 ~/KIMORE）")
    ap.add_argument("--no-hash", action="store_true", help="只比大小，不算哈希")
    a = ap.parse_args()

    root = Path(a.root).expanduser().resolve()
    if not root.exists():
        print(f"[error] 目录不存在: {root}", file=sys.stderr)
        return 1
    if not SUMS.exists():
        print(f"[error] 校验清单不存在: {SUMS}", file=sys.stderr)
        return 1

    print(f"校验清单: {SUMS.relative_to(ROOT)}")
    print(f"数据目录: {root}\n")

    ok = missing = bad = 0
    for digest, name, size, note in parse_sums(SUMS):
        path = root / name
        label = f"{name} ({size / 1024 / 1024:.1f} MB)"
        if not path.exists():
            # 允许哈希前缀不同的同类文件：按关键字匹配（如 CG-*.zip）
            alts = sorted(root.glob(f"{name.split('-')[0]}*.zip"))
            if alts:
                path = alts[0]
                label = f"{path.name} ({path.stat().st_size / 1024 / 1024:.1f} MB)"
        if not path.exists():
            print(f"[缺失] {name}  —— {note}")
            missing += 1
            continue
        got_size = path.stat().st_size
        if got_size != size:
            print(f"[大小不符] {label}: 期望 {size} 实际 {got_size}")
            bad += 1
            continue
        if a.no_hash:
            print(f"[通过·仅大小] {label}")
            ok += 1
            continue
        got = sha256_file(path)
        if got == digest:
            print(f"[通过] {label}")
            ok += 1
        else:
            print(f"[哈希不符] {label}\n         期望 {digest}\n         实际 {got}")
            bad += 1

    print(f"\n合计: 通过 {ok} / 缺失 {missing} / 失败 {bad}")
    if missing or bad:
        print("提示：缺文件下载后放到同一目录；只需要跑评估内核的话，"
              "archive.zip 解压出 Kimore/ 就够（不含 .m 与 AVI）。")
        return 1
    print("数据完整，可以启动 mcp_server：python mcp_server/server.py --port 9100 --data-root <Kimore 根目录>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
