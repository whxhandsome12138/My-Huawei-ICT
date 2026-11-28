#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""KIMORE 评估内核 —— 离线回放 MCP Server（C 侧联调替身）

用途
----
在 B 的真实服务（exercise-assessment-kimore，SSE /sse，端口 8001）不可达时，
用 B 交付包里的真实响应样例复刻同构接口，让 Agent / Skill / 提示词可以
在本地先跑通，联调时只改 endpoint 一行即可切换。

设计原则
--------
1. 线级同构：工具名、参数名、默认值、枚举、信封字段与 contracts/tool_schemas_frozen.json 一致。
2. 数值不改写：命中样例的响应逐字节来自 B 导出的 JSON，只替换 request_id。
3. 覆盖面诚实：每条响应在 provenance.replay.coverage 里标注 exact / derived / absent / synthetic，
   非 exact 的额外追加一条 warning，避免把替身数据当真实服务结果引用。

启动
----
python server.py --port 9100
样例默认读同目录 fixtures/（从 B 交付包 contracts/examples 复制，10 个 JSON）。
端点 http://127.0.0.1:9100/sse （SSE 主用）；同时暴露 /mcp （Streamable HTTP 兜底）。
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import uuid
from typing import Annotated, Any, Literal

from pydantic import Field
from mcp.server.fastmcp import FastMCP

SAMPLE_RE = re.compile(r"^Es[1-5]-[0-9a-f]{20}$")
EXERCISE_RE = re.compile(r"^Es[0-9]+$")

SERVER_NAME = "exercise-assessment-kimore-replay"
SCHEMA_VERSION = "1.0.0"

# 真实服务当前唯一支持的样本（B 的交付包只给了这一条 assess / explain 明细）
FULL_SAMPLE = "Es2-467acf3acb6a8191d6ef"
# 第二条真实样例：1.0.0 起由真实服务抓取完整 17 特征（fixtures/real_assess_second.json）
SECOND_SAMPLE = "Es2-fbab3ba3e46a4ea94233"

# 清单里可见、但没有明细响应的样本（list_samples 的 5 条）
KNOWN_LISTED = {
    "Es2-467acf3acb6a8191d6ef",
    "Es2-cf07c9a6cc350b8b0f1d",
    "Es2-c149ce6b79d5bea4d267",
    "Es2-099f0f68b24e82697bc2",
    "Es2-446ffdeee3d1f3c5e738",
}

FIXTURE_DIR = ""
_CACHE: dict[str, dict] = {}
_CRITERIA_BY_ID: dict[str, dict] = {}


def fixture(name: str) -> dict:
    if name not in _CACHE:
        path = os.path.join(FIXTURE_DIR, name)
        with open(path, "r", encoding="utf-8") as fh:
            _CACHE[name] = json.load(fh)
    return _CACHE[name]


def criteria_features() -> dict[str, dict]:
    if not _CRITERIA_BY_ID:
        for item in fixture("real_query_criteria.json")["data"]["features"]:
            _CRITERIA_BY_ID[item["feature_id"]] = item
    return _CRITERIA_BY_ID


REPLAY_WARNING = (
    "【回放模式】本响应对应 {coverage} 覆盖面（fixture={name}），"
    "用于离线联调；线上联调请以 B 的真实服务返回为准。"
)


def serve(name: str, coverage: str = "exact", note: str = "") -> dict:
    """回放一条真实样例：只换 request_id，其余字段原样返回。"""
    env = copy.deepcopy(fixture(name))
    env["request_id"] = str(uuid.uuid4())
    prov = env.setdefault("provenance", {})
    prov["replay"] = {
        "mode": "offline_fixture",
        "fixture": name,
        "coverage": coverage,
        "note": note,
    }
    if coverage != "exact":
        env.setdefault("warnings", []).append(REPLAY_WARNING.format(coverage=coverage, name=name))
    return env


def business_error(code: str, message: str, retryable: bool = False, template: str = "real_error_model_unavailable.json") -> dict:
    """按真实服务的错误信封结构生成业务错误（用于 B 已声明但未给样例的路径）。"""
    env = copy.deepcopy(fixture(template))
    env["request_id"] = str(uuid.uuid4())
    env["status"] = "error"
    env["data"] = None
    env["error"] = {"code": code, "message": message, "retryable": retryable}
    env["provenance"]["replay"] = {
        "mode": "offline_fixture",
        "fixture": template,
        "coverage": "synthetic",
        "note": "B 已声明该行为但交付包未提供样例响应，这里按其错误信封结构复刻。",
    }
    env.setdefault("warnings", []).append(
        REPLAY_WARNING.format(coverage="synthetic", name=template) + " 该错误码由回放服务按声明复刻。"
    )
    return env


def partial_like(env: dict, warning: str) -> dict:
    env = copy.deepcopy(env)
    env["status"] = "partial"
    env.setdefault("warnings", []).append(warning)
    return env


def second_sample_response() -> dict:
    """第二条真实样例：1.0.0 的完整响应，由真实服务抓取。"""
    return serve("real_assess_second.json")


mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "KIMORE 动作评估内核的离线回放替身。所有响应来自 B 交付包的真实样例，"
        "provenance.replay.coverage != exact 表示该条不是完整真实覆盖。"
    ),
    host="0.0.0.0",
    port=9100,
)


@mcp.tool(
    name="list_samples",
    description="列出可用于评估的样本（回放模式最多返回 5 条，total_available 为真实可用总数）。",
)
def list_samples(
    exercise_id: str | None = None,
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
) -> dict:
    if exercise_id is not None:
        if not EXERCISE_RE.match(exercise_id.strip()):
            return business_error("INVALID_ARGUMENT", "exercise_id 必须形如 Es2；不接受路径、空格或 URL。", False, "real_error_invalid_argument.json")
        if exercise_id.strip() != "Es2":
            return business_error(
                "UNSUPPORTED_EXERCISE",
                f"当前评估内核只支持 Es2（躯干侧倾），{exercise_id} 尚未接入。",
                False,
            )
    env = serve("real_list_samples.json")
    samples = env["data"]["samples"][:limit]
    env["data"]["samples"] = samples
    if len(samples) < limit:
        env["warnings"].append(
            f"回放模式只提供 {len(samples)} 条样本明细；线上服务按 total_available=77 分页。"
        )
    return env


@mcp.tool(
    name="assess_exercise",
    description=(
        "对一条录制做运动学评估，返回质量位、17 个特征、历史临床评分、参照分布与偏离项。"
        "predicted_score 恒为 null（未验证任何预测模型）。"
    ),
)
def assess_exercise(
    sample_id: str,
    mode: Literal["kinematics", "observed_label", "baseline_prediction"] = "kinematics",
) -> dict:
    sid = (sample_id or "").strip()
    if mode == "baseline_prediction":
        return serve("real_error_model_unavailable.json")
    if not SAMPLE_RE.match(sid):
        return serve("real_error_invalid_argument.json")
    if sid == FULL_SAMPLE:
        if mode == "observed_label":
            return serve("real_assess_observed_label.json")
        return serve("real_assess_success.json")
    if sid == SECOND_SAMPLE:
        if mode == "observed_label":
            env = serve("real_assess_observed_label.json", coverage="derived", note="样本 #2 的历史评分单独提供")
            data = env["data"]
            data["sample_id"] = SECOND_SAMPLE
            data["assessment_id"] = "17bfb7dc3544939e"
            data["quality"] = {"status": "pass", "n_frames": 587, "valid_frames": 586, "valid_frame_ratio": 0.9983, "reasons": []}
            data["observed_label"] = {
                "cTS": 16.0, "cPO": 5.0, "cCF": 11.0,
                "label_kind": "historical_clinician",
                "label_level": "subject_exercise",
                "note": "历史临床评分，受试者×动作粒度，不是本次录制或单次重复的分数。",
            }
            return env
        return second_sample_response()
    if sid in KNOWN_LISTED:
        env = serve("real_assess_success.json", coverage="absent", note="该样本在清单中可见，但交付包未提供其明细响应")
        data = env["data"]
        data["sample_id"] = sid
        data["features"] = []
        data["deviations"] = []
        data["reference"] = None
        return partial_like(
            env,
            "【回放模式】该样本只有清单条目，没有明细响应；返回的是结构件，数值不可引用。",
        )
    return serve("real_error_sample_not_found.json")


@mcp.tool(
    name="explain_deviation",
    description="返回某项特征相对同类参照的差异、方向与对应帧证据；可用 feature_id 过滤。",
)
def explain_deviation(sample_id: str, feature_id: str | None = None) -> dict:
    sid = (sample_id or "").strip()
    if not SAMPLE_RE.match(sid):
        return serve("real_error_invalid_argument.json")
    if sid == FULL_SAMPLE:
        env = serve("real_explain_deviation.json")
    elif sid == SECOND_SAMPLE:
        env = serve("real_explain_second.json")
    elif sid in KNOWN_LISTED:
        env = serve("real_explain_deviation.json", coverage="absent", note="该样本无明细")
        env["data"]["sample_id"] = sid
        env["data"]["evidence"] = []
        env = partial_like(env, "【回放模式】该样本只有清单条目，无偏离明细。")
    else:
        return serve("real_error_sample_not_found.json")
    if feature_id and feature_id not in criteria_features():
        # 真实服务对未知 feature_id 返回业务错误，而不是空证据
        return business_error(
            "FEATURE_UNAVAILABLE",
            "该样本没有这个 feature_id；可用值见 assess_exercise 的 features。",
        )
    if feature_id:
        data = env.get("data") or {}
        kept = [item for item in data.get("evidence", []) if item.get("feature_id") == feature_id]
        data["evidence"] = kept
        if not kept:
            env.setdefault("warnings", []).append(
                f"本次评估的证据里没有 {feature_id}；它可能未触发偏离，或不在 Es2 的可判定特征集内。"
            )
    return env


@mcp.tool(
    name="query_criteria",
    description="查询某个动作的判定口径：特征清单、单位、证据等级、论文出处与不可得项。",
)
def query_criteria(exercise_id: str) -> dict:
    eid = (exercise_id or "").strip()
    if not EXERCISE_RE.match(eid):
        return business_error("INVALID_ARGUMENT", "exercise_id 必须形如 Es2。", False, "real_error_invalid_argument.json")
    if eid != "Es2":
        return business_error(
            "UNSUPPORTED_EXERCISE",
            f"当前评估内核只支持 Es2；{eid} 的判定口径尚未冻结。",
            False,
        )
    return serve("real_query_criteria.json")


@mcp.tool(
    name="plan_session",
    description="把 1–5 条录制放在一起比较，返回可比性提醒与不可提供的结论类型。不输出诊断或处方。",
)
def plan_session(sample_ids: Annotated[list[str], Field(min_length=1, max_length=5)]) -> dict:
    ids = [(s or "").strip() for s in sample_ids]
    for sid in ids:
        if not SAMPLE_RE.match(sid):
            return serve("real_error_invalid_argument.json")
    if len(set(ids)) != len(ids):
        return business_error("INVALID_ARGUMENT", "sample_ids 不能重复；同一录制只比较一次。", False, "real_error_invalid_argument.json")
    unknown = [s for s in ids if s not in KNOWN_LISTED and s != FULL_SAMPLE and s != SECOND_SAMPLE]
    if unknown:
        return serve("real_error_sample_not_found.json")
    env = serve("real_plan_session.json")
    records = {r["sample_id"]: r for r in env["data"]["records"]}
    kept = [records[s] for s in ids if s in records]
    if len(kept) != len(ids):
        env["data"]["records"] = kept
        env = partial_like(
            env,
            f"【回放模式】只有 {len(kept)}/{len(ids)} 条记录有可比数据；其余记录在线上服务中才会返回。",
        )
    env["data"]["requested_sample_ids"] = ids
    return env


def main() -> None:
    global FIXTURE_DIR
    parser = argparse.ArgumentParser(description="KIMORE 评估内核离线回放 MCP Server")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--fixtures",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures",
        ),
    )
    args = parser.parse_args()
    FIXTURE_DIR = os.path.abspath(args.fixtures)
    if not os.path.isdir(FIXTURE_DIR):
        sys.exit(f"样例目录不存在：{FIXTURE_DIR}")
    fixture("real_assess_success.json")  # 预加载，早失败
    mcp.settings.port = args.port
    mcp.settings.host = args.host
    print(f"[replay] {SERVER_NAME}  fixtures={FIXTURE_DIR}")
    print(f"[replay] SSE  http://{args.host}:{args.port}/sse")
    print(f"[replay] HTTP http://{args.host}:{args.port}/mcp")
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
