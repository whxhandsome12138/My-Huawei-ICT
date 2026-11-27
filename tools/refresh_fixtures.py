"""从真实 MCP 服务重新抓取 fixtures。

用途：B 发布新的接口版本（例如 1.0.0 修正左侧符号）后，回放服务里的 9 个
fixture 会变成旧值。用这个脚本对着真实服务跑一遍，把 fixtures/*.json 整体刷新，
回放服务与自检脚本就自动跟上新契约，不用手改任何数字。

用法：

    # 先确认真实服务在监听（B 的机器或本机）
    python tools/refresh_fixtures.py --host 192.168.138.1 --port 8001

    # 只看会变什么，不落盘
    python tools/refresh_fixtures.py --host 127.0.0.1 --port 9300 --dry-run

    # 抓完顺手跑自检
    python tools/refresh_fixtures.py --host 127.0.0.1 --port 9300 --verify

抓取顺序与 fixtures/INDEX.json 一一对应。凡是服务返回的东西都原样保存，
不做任何加工——这个脚本的职责只是搬运。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FIXTURES = REPO / "mcp_server" / "fixtures"

FULL = "Es2-467acf3acb6a8191d6ef"
SECOND = "Es2-fbab3ba3e46a4ea94233"

# (文件名, 工具名, 参数)  —— 与 INDEX.json 的登记顺序一致
CAPTURE_PLAN = [
    ("real_list_samples.json", "list_samples", {}),
    ("real_assess_success.json", "assess_exercise", {"sample_id": FULL}),
    ("real_assess_observed_label.json", "assess_exercise",
     {"sample_id": FULL, "mode": "observed_label"}),
    ("real_assess_second.json", "assess_exercise", {"sample_id": SECOND}),
    ("real_explain_deviation.json", "explain_deviation", {"sample_id": FULL}),
    ("real_explain_second.json", "explain_deviation", {"sample_id": SECOND}),
    ("real_query_criteria.json", "query_criteria", {"exercise_id": "Es2"}),
    ("real_plan_session.json", "plan_session", {"sample_ids": [FULL, SECOND]}),
    ("real_error_sample_not_found.json", "assess_exercise",
     {"sample_id": "Es2-00000000000000000000"}),
    ("real_error_invalid_argument.json", "assess_exercise",
     {"sample_id": "../../Kimore"}),
    ("real_error_model_unavailable.json", "assess_exercise",
     {"sample_id": FULL, "mode": "baseline_prediction"}),
]


def envelope_of(result) -> dict:
    """从一个 CallToolResult 里取出统一信封。"""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and structured:
        # FastMCP 会把它包在 {"result": ...} 里，两种情况都兼容
        return structured.get("result", structured)
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    raise RuntimeError("响应里既没有 structuredContent 也没有 text content")


def diff_summary(old: dict, new: dict) -> list[str]:
    """粗略列出顶层 status 与特征值的变化，够用即可。"""
    out = []
    if old.get("status") != new.get("status"):
        out.append(f"status {old.get('status')} -> {new.get('status')}")
    # query_criteria 的 features 是口径描述，没有 value 键；用 get 避免 KeyError
    # 错误响应的 data 是 null，不能直接 .get；query_criteria 的 features 也没有 value 键
    ov = {f["feature_id"]: f.get("value")
          for f in ((old.get("data") or {}).get("features") or [])
          if isinstance(f, dict) and "feature_id" in f}
    nv = {f["feature_id"]: f.get("value")
          for f in ((new.get("data") or {}).get("features") or [])
          if isinstance(f, dict) and "feature_id" in f}
    for k in sorted(set(ov) & set(nv)):
        if ov[k] != nv[k]:
            out.append(f"{k}: {ov[k]} -> {nv[k]}")
    return out


async def capture(host: str, port: int, dry: bool) -> int:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = f"http://{host}:{port}/sse"
    print(f"[refresh] 连接 {url}")
    changed = 0
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            print(f"[refresh] 服务暴露 {len(tools)} 个工具: {', '.join(sorted(tools))}")
            for filename, tool, args in CAPTURE_PLAN:
                if tool not in tools:
                    print(f"[skip] {filename}: 服务没有 {tool}")
                    continue
                env = envelope_of(await session.call_tool(tool, args))
                replay = (env.get("provenance") or {}).get("replay")
                if replay:
                    print("[abort] 对方是回放服务（响应里带 provenance.replay），"
                          "刷新会把自己的 fixture 又写回去。请指向 B 的真实服务。",
                          file=sys.stderr)
                    return 1
                path = FIXTURES / filename
                old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                changes = diff_summary(old, env)
                payload = json.dumps(env, ensure_ascii=False, indent=2) + "\n"
                if not dry and payload != (path.read_text(encoding="utf-8") if path.exists() else None):
                    path.write_text(payload, encoding="utf-8", newline="\n")
                tag = "changed" if changes else "same"
                if changes:
                    changed += 1
                print(f"[{tag}] {filename} ({len(payload)} B)")
                for line in changes[:12]:
                    print(f"        {line}")
    print(f"[refresh] 完成：{changed} 个 fixture 有变化" + ("（dry-run，未落盘）" if dry else ""))
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="从真实 MCP 服务刷新 fixtures")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--dry-run", action="store_true", help="只打印差异，不写文件")
    ap.add_argument("--verify", action="store_true", help="刷新后跑一遍 selfcheck")
    a = ap.parse_args()

    # 回环请求不要走系统代理（Windows 上很常见）
    for key in ("NO_PROXY", "no_proxy"):
        parts = [p for p in os.environ.get(key, "").split(",") if p]
        for host in ("127.0.0.1", "localhost", "::1", a.host):
            if host not in parts:
                parts.append(host)
        os.environ[key] = ",".join(parts)

    try:
        asyncio.run(capture(a.host, a.port, a.dry_run))
    except Exception as exc:  # noqa: BLE001
        print(f"[refresh] 失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if a.verify and not a.dry_run:
        import subprocess
        return subprocess.call([sys.executable, str(REPO / "mcp_server" / "selfcheck.py"),
                                "--port", str(a.port)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
