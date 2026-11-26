"""校验「腰衡」本体与 SHACL 约束。

用法：
    python tools/validate_ontology.py

做四件事：
1. 三个 .ttl 能被 rdflib 解析（语法与 IRI 合法性）；
2. 用 shapes.ttl 校验 ontology.ttl + features.ttl + examples_good.ttl，期望通过；
3. 用同一套 shapes 校验 examples_bad.ttl，期望**不通过**且命中预期条款（证明约束真的生效）；
4. 把两次结果写成 deliver/ontology/validation_report.md，供答辩截图。
"""
from __future__ import annotations

import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
# 两处布局都支持：C_delivery 下是 deliver/ontology，开源仓库根下是 ontology/
_candidates = [ROOT / "ontology", ROOT / "deliver" / "ontology"]
ONT_DIR = next((p for p in _candidates if p.is_dir()), _candidates[0])
ONT = ONT_DIR / "ontology.ttl"
FEATURES = ONT_DIR / "features.ttl"
SHAPES = ONT_DIR / "shapes.ttl"
GOOD = ONT_DIR / "examples_good.ttl"
BAD = ONT_DIR / "examples_bad.ttl"
REPORT = ONT_DIR / "validation_report.md"


def load(path: Path, graph: Graph | None = None) -> Graph:
    g = graph or Graph()
    g.parse(path, format="turtle")  # 语法错误会直接抛
    return g


def run(data: Graph, shapes: Graph) -> tuple[bool, str]:
    conforms, _, text = validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="none",
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
        serialize_report_graph=False,
    )
    return conforms, text


def main() -> int:
    for p in (ONT, FEATURES, SHAPES, GOOD, BAD):
        if not p.exists():
            print(f"missing: {p}")
            return 2

    base = load(ONT)
    load(FEATURES, base)
    load(GOOD, base)
    shapes = load(SHAPES)

    good_ok, good_text = run(base, shapes)

    bad_data = load(ONT)
    load(FEATURES, bad_data)
    load(GOOD, bad_data)
    load(BAD, bad_data)
    bad_ok, bad_text = run(bad_data, shapes)

    # 期望：合规模块通过；违规模块必须被拦下，且至少 4 条结果
    bad_count = bad_text.count("Constraint Violation")
    expectations = [
        ("合规实例通过约束", good_ok is True),
        ("违规实例被拦下", bad_ok is False),
        ("违规原因不少于 4 条", bad_count >= 4),
    ]
    all_ok = all(passed for _, passed in expectations)

    lines = [
        "# 本体与 SHACL 约束校验报告",
        "",
        f"数据图：`ontology.ttl`（{len(load(ONT))} 三元组）+ `features.ttl`"
        f"（{len(load(FEATURES))} 三元组）+ `examples_good.ttl`",
        f"约束图：`shapes.ttl`（{len(shapes)} 三元组）",
        "",
        "## 一、期望",
        "",
        "| 检查项 | 结果 |",
        "| :-- | :-- |",
    ]
    lines += [f"| {name} | {'通过' if passed else '未通过'} |" for name, passed in expectations]
    lines += [
        "",
        "## 二、合规实例（期望通过）",
        "",
        f"**Conforms: {good_ok}**",
        "",
        "```",
        good_text.strip()[:3000],
        "```",
        "",
        "## 三、违规实例（期望被拦下）",
        "",
        f"**Conforms: {bad_ok}**，命中 {bad_count} 条。",
        "",
        "```",
        bad_text.strip()[:6000],
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    for name, passed in expectations:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"good conforms={good_ok}  bad conforms={bad_ok}  bad violations={bad_count}")
    print(f"report: {REPORT}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
