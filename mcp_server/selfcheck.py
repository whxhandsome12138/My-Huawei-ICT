#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""回放 MCP 的自动验收脚本（等于提前跑一遍 T14 联调清单）。

先起服务： python server.py --port 9100
再跑验收： python selfcheck.py --port 9100 --out reports

逐项比对 B 在交付包里声明的数值与错误语义，输出 PASS/FAIL 表，
并写出 Markdown 报告，可直接贴进 CHECKLIST_回填.md。
线上联调时只需把 --port 指向 B 的 8001，断言不用改。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from typing import Any, Awaitable, Callable

from mcp import ClientSession
from mcp.client.sse import sse_client

# 本机若开着系统代理（Windows WinINET / 企业代理），httpx 会读环境后把 127.0.0.1 的请求
# 也转给代理，表现是 /sse 返回 502 Bad Gateway。这里默认把回环地址排除，不动用户的代理设置。
_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
for _host in ("127.0.0.1", "localhost"):
    if _host not in _no_proxy:
        _no_proxy = f"{_no_proxy},{_host}" if _no_proxy else _host
os.environ["NO_PROXY"] = _no_proxy
os.environ["no_proxy"] = _no_proxy

FULL = "Es2-467acf3acb6a8191d6ef"
SECOND = "Es2-fbab3ba3e46a4ea94233"

EXPECTED_TOOLS = {"assess_exercise", "explain_deviation", "query_criteria", "plan_session", "list_samples"}
EXPECTED_PROPS = {
    "assess_exercise": {"sample_id", "mode"},
    "explain_deviation": {"sample_id", "feature_id"},
    "query_criteria": {"exercise_id"},
    "plan_session": {"sample_ids"},
    "list_samples": {"exercise_id", "limit"},
}

CheckFn = Callable[[], Awaitable[tuple[bool, str]]]


class Checker:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def check(self, section: str, name: str, fn: CheckFn) -> None:
        start = time.perf_counter()
        try:
            ok, detail = await fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"异常：{type(exc).__name__}: {exc}"
            traceback.print_exc()
        cost = (time.perf_counter() - start) * 1000
        self.rows.append({"section": section, "name": name, "ok": ok, "detail": detail, "ms": cost})
        print(f"[{'PASS' if ok else 'FAIL'}] {section} / {name}  ({cost:.0f} ms)  {detail}")


def envelope_of(result: Any) -> dict:
    sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict) and "status" in sc:
        return sc
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            payload = json.loads(text)
            if isinstance(payload, dict) and "status" in payload:
                return payload
    raise AssertionError("返回里找不到统一信封（status 字段）")


def bytes_of(result: Any) -> int:
    total = 0
    for block in getattr(result, "content", []) or []:
        total += len((getattr(block, "text", "") or "").encode("utf-8"))
    return total


def feature_values(env: dict) -> dict[str, float]:
    return {f["feature_id"]: f["value"] for f in ((env.get("data") or {}).get("features") or [])}


async def run(port: int, out_dir: str, host: str = "127.0.0.1") -> int:
    url = f"http://{host}:{port}/sse"
    ck = Checker()

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            async def t_tools() -> tuple[bool, str]:
                names = {t.name for t in tools.tools}
                return names == EXPECTED_TOOLS, f"get={sorted(names)}"

            await ck.check("A 发现", "五个工具全部暴露", t_tools)

            async def t_props() -> tuple[bool, str]:
                bad = []
                for tool in tools.tools:
                    props = set((tool.inputSchema or {}).get("properties", {}))
                    if props != EXPECTED_PROPS.get(tool.name, props):
                        bad.append(f"{tool.name}:{sorted(props)}")
                return not bad, "参数集一致" if not bad else f"不一致 {bad}"

            await ck.check("A 发现", "inputSchema 参数集与冻结契约一致", t_props)

            async def call(name: str, args: dict) -> dict:
                return envelope_of(await session.call_tool(name, args))

            # ---------------- B 逐个工具调用 ----------------
            async def t_list() -> tuple[bool, str]:
                env = await call("list_samples", {})
                d = env["data"]
                ok = env["status"] == "ok" and d["total_available"] == 77 and len(d["samples"]) == 5
                return ok, f"status={env['status']} samples={len(d['samples'])} total={d['total_available']}"

            await ck.check("B 工具", "list_samples 默认 5 条 / total=77", t_list)

            async def t_list_limit() -> tuple[bool, str]:
                env = await call("list_samples", {"limit": 2})
                return len(env["data"]["samples"]) == 2, f"samples={len(env['data']['samples'])}"

            await ck.check("B 工具", "list_samples limit=2 生效", t_list_limit)

            async def t_assess() -> tuple[bool, str]:
                raw = await session.call_tool("assess_exercise", {"sample_id": FULL})
                env = envelope_of(raw)
                vals = feature_values(env)
                # 只断言「不随符号约定变化」的数值：range 与右侧峰在 1.0.0 / 1.1.0 都同值。
                # 左侧峰的符号在 1.1.0 会翻正（作者口径），故不在此断言，见 docs/FEATURE_PROVENANCE.md §3。
                # deviations 条数会随符号修正浮动，断言「有偏离点且不超过 5 条」。
                ok = (
                    env["status"] == "ok"
                    and len(vals) == 17
                    and abs(vals.get("torso_tilt_left_range", 0) - 37.489) < 1e-6
                    and abs(vals.get("torso_tilt_right_peak", 0) - 20.901) < 1e-6
                    and env["data"]["observed_label"]["cTS"] == 45.0
                    and env["data"]["predicted_score"] is None
                    and 1 <= len(env["data"]["deviations"]) <= 5
                )
                return ok, f"features={len(vals)} left_range={vals.get('torso_tilt_left_range')} cTS={env['data']['observed_label']['cTS']} dev={len(env['data']['deviations'])} bytes={bytes_of(raw)}"

            await ck.check("B 工具", "assess_exercise 17 特征 + cTS + predicted=null", t_assess)

            async def t_assess_label() -> tuple[bool, str]:
                env = await call("assess_exercise", {"sample_id": FULL, "mode": "observed_label"})
                d = env["data"]
                ok = env["status"] == "ok" and d["mode"] == "observed_label" and d["features"] == [] and d["observed_label"]["cTS"] == 45.0
                return ok, f"mode={d['mode']} features={len(d['features'])} cTS={d['observed_label']['cTS']}"

            await ck.check("B 工具", "assess_exercise mode=observed_label", t_assess_label)

            async def t_assess_second() -> tuple[bool, str]:
                env = await call("assess_exercise", {"sample_id": SECOND})
                vals = feature_values(env)
                ok = env["status"] == "partial" and len(vals) == 11 and abs(vals.get("torso_tilt_left_range", 0) - 25.653) < 1e-6
                return ok, f"status={env['status']} features={len(vals)} left_range={vals.get('torso_tilt_left_range')}"

            await ck.check("B 工具", "assess_exercise 样本#2 走 partial（11/17）", t_assess_second)

            async def t_explain() -> tuple[bool, str]:
                env = await call("explain_deviation", {"sample_id": FULL})
                items = env["data"]["evidence"]
                ok = env["status"] == "ok" and len(items) == 3 and all("reference" in i for i in items)
                return ok, f"evidence={len(items)} not_evidence_of={len(env['data'].get('not_evidence_of', []))}"

            await ck.check("B 工具", "explain_deviation 返回 3 条证据 + 参照分位", t_explain)

            async def t_explain_filter() -> tuple[bool, str]:
                env = await call("explain_deviation", {"sample_id": FULL, "feature_id": "torso_tilt_right_peak"})
                items = env["data"]["evidence"]
                ok = len(items) == 1 and items[0]["feature_id"] == "torso_tilt_right_peak" and abs(items[0]["difference"] + 4.068) < 1e-6
                return ok, f"evidence={len(items)} diff={items[0]['difference'] if items else None}"

            await ck.check("B 工具", "explain_deviation feature_id 过滤", t_explain_filter)

            async def t_criteria() -> tuple[bool, str]:
                env = await call("query_criteria", {"exercise_id": "Es2"})
                d = env["data"]
                ok = env["status"] == "ok" and len(d["features"]) == 17 and d["expected_repetitions"] == 5 and len(d["unavailable"]) == 5
                return ok, f"features={len(d['features'])} reps={d['expected_repetitions']} unavailable={len(d['unavailable'])}"

            await ck.check("B 工具", "query_criteria Es2 口径完整", t_criteria)

            async def t_plan() -> tuple[bool, str]:
                env = await call("plan_session", {"sample_ids": [FULL, SECOND]})
                d = env["data"]
                ok = env["status"] == "ok" and len(d["records"]) == 2 and len(d["not_provided"]) == 4
                return ok, f"records={len(d['records'])} not_provided={len(d['not_provided'])}"

            await ck.check("B 工具", "plan_session 两条记录可比", t_plan)

            # ---------------- C 五类失败路径 ----------------
            async def t_not_found() -> tuple[bool, str]:
                env = await call("assess_exercise", {"sample_id": "Es2-ffffffffffffffffffff"})
                e = env["error"] or {}
                ok = env["status"] == "error" and e.get("code") == "SAMPLE_NOT_FOUND" and e.get("retryable") is False
                return ok, f"code={e.get('code')} retryable={e.get('retryable')}"

            await ck.check("C 失败", "未知 ID → SAMPLE_NOT_FOUND", t_not_found)

            async def t_traversal() -> tuple[bool, str]:
                env = await call("assess_exercise", {"sample_id": "../../Kimore"})
                e = env["error"] or {}
                return e.get("code") == "INVALID_ARGUMENT", f"code={e.get('code')}"

            await ck.check("C 失败", "路径穿越 → INVALID_ARGUMENT", t_traversal)

            async def t_model() -> tuple[bool, str]:
                env = await call("assess_exercise", {"sample_id": FULL, "mode": "baseline_prediction"})
                e = env["error"] or {}
                ok = e.get("code") == "MODEL_UNAVAILABLE" and e.get("retryable") is False
                return ok, f"code={e.get('code')} retryable={e.get('retryable')}"

            await ck.check("C 失败", "预测模式 → MODEL_UNAVAILABLE", t_model)

            async def t_unsupported() -> tuple[bool, str]:
                env = await call("query_criteria", {"exercise_id": "Es9"})
                e = env["error"] or {}
                return e.get("code") == "UNSUPPORTED_EXERCISE", f"code={e.get('code')}"

            await ck.check("C 失败", "未接入动作 → UNSUPPORTED_EXERCISE", t_unsupported)

            async def t_dup() -> tuple[bool, str]:
                env = await call("plan_session", {"sample_ids": [FULL, FULL]})
                e = env["error"] or {}
                return e.get("code") == "INVALID_ARGUMENT", f"code={e.get('code')}"

            await ck.check("C 失败", "重复 ID → INVALID_ARGUMENT", t_dup)

            async def t_partial() -> tuple[bool, str]:
                env = await call("explain_deviation", {"sample_id": SECOND})
                ok = env["status"] == "partial" and ((env.get("data") or {}).get("evidence") or []) == []
                return ok, f"status={env['status']} evidence={len((env.get('data') or {}).get('evidence') or [])}"

            await ck.check("C 失败", "缺明细 → partial（不抛异常）", t_partial)

    passed = sum(1 for r in ck.rows if r["ok"])
    total = len(ck.rows)
    print(f"\n===== {passed}/{total} PASS =====")

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "replay_selfcheck.md")
    lines = [
        "# 回放 MCP 自动验收报告",
        "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 端点：http://127.0.0.1:{port}/sse",
        f"- 结论：**{passed}/{total} 通过**",
        "",
        "| 分组 | 检查项 | 结果 | 说明 | 耗时(ms) |",
        "| :-- | :-- | :-- | :-- | --: |",
    ]
    for r in ck.rows:
        lines.append(f"| {r['section']} | {r['name']} | {'PASS' if r['ok'] else '**FAIL**'} | {r['detail']} | {r['ms']:.0f} |")
    lines += [
        "",
        "> 本报告由 `selfcheck.py` 针对**离线回放服务**生成，不等于线上联调结论；",
        "> 线上联调时把 `--port` 指向 B 的 8001，其余断言不变。",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"report: {path}")
    return 0 if passed == total else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="回放 MCP 自动验收")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--host", default="127.0.0.1", help="MCP 主机；测 B 的服务时填他的私网 IP")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports"))
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.port, args.out, args.host)))


if __name__ == "__main__":
    main()
