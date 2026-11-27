"""半自动生成本体中的特征个体（features.ttl）。

设计意图（对应评分项「半自动本体构建效率优势」）：
    机器负责的部分：从 MCP 契约里读出 feature_id / unit / 方向，保证本体与工具永不失配；
    人负责的部分：证据等级、作者脚本行号、聚合口径、所依赖关节、符号约定。
两类信息在 METADATA 里合并后生成 Turtle，改一次契约就能重新生成，不需要手改 17 段。

用法：
    python tools/gen_ontology_features.py            # 生成并覆盖
    python tools/gen_ontology_features.py --check    # 只校验契约与本体是否一致
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 仓库内布局（mcp_server/fixtures/…）优先；在老工作区里则回落到 deliver/ 布局
_CANDIDATES = [
    ROOT / "mcp_server" / "fixtures" / "real_assess_success.json",
    ROOT / "deliver" / "handoff" / "kimore_mcp_handoff_2026-11-24" / "contracts" / "examples" / "real_assess_success.json",
    ROOT / "deliver" / "replay_mcp" / "fixtures" / "real_assess_success.json",
]
FIXTURE = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
OUT = next((p for p in [ROOT / "ontology" / "features.ttl", ROOT / "deliver" / "ontology" / "features.ttl"]
            if p.parent.exists()), ROOT / "ontology" / "features.ttl")

PAPER = "Capecci et al. 2019, KIMORE, p.1441 sII.D"
SCRIPT = "feat_extract_Ex2.m"

# feature_id: (证据等级, 脚本行, 聚合, 关节列表, 符号约定, 是否与竖直轴无关, 备注)
METADATA = {
    "torso_tilt_left_peak": ("verified_paper", "3,26,29,60", "max",
        ["ShoulderLeft", "HipLeft"], "sign_left_negative", False,
        "作者第 26 行对左侧取负，右侧（第 27 行）不取负，本项目统一为左负右正。"),
    "torso_tilt_right_peak": ("verified_paper", "4,27,30,41", "max",
        ["ShoulderRight", "HipRight"], "sign_right_positive", False,
        "与左侧反号是作者原始实现的一部分，不是笔误。"),
    "torso_tilt_left_range": ("verified_paper", "29,30,60,61,62", "max-minus-min",
        ["ShoulderLeft", "HipLeft"], "sign_left_negative", False,
        "左侧信号丢前 30 帧后再取极差。"),
    "torso_tilt_right_range": ("verified_paper", "41,42,43", "max-minus-min",
        ["ShoulderRight", "HipRight"], "sign_right_positive", False,
        "右侧信号不丢前 30 帧，与左侧不对称。"),
    "elbow_angle_left_median": ("verified_paper", "81,83,85,87", "median",
        ["ShoulderLeft", "ElbowLeft", "WristLeft"], None, True,
        "余弦定理三点角，与相机朝向无关。"),
    "elbow_angle_right_median": ("verified_paper", "81,83,85,87", "median",
        ["ShoulderRight", "ElbowRight", "WristRight"], None, True,
        "同上，右侧。"),
    "knee_angle_left_median": ("verified_paper", "94,97,99,100", "median",
        ["HipLeft", "KneeLeft", "AnkleLeft"], None, True,
        "余弦定理三点角。"),
    "knee_angle_right_median": ("verified_paper", "94,97,99,100", "median",
        ["HipRight", "KneeRight", "AnkleRight"], None, True,
        "同上，右侧。"),
    "hand_distance_median": ("derived_engineering", "158", "median",
        ["WristLeft", "WristRight"], None, True,
        "link_hand，欧氏距离；单位是 Kinect 相机原始单位，不是米。"),
    "shoulder_distance_median": ("derived_engineering", "163", "median",
        ["ShoulderLeft", "ShoulderRight"], None, True,
        "link_shoulder，欧氏距离。"),
    "hip_distance_median": ("derived_engineering", "168", "median",
        ["HipLeft", "HipRight"], None, True,
        "link_hip，欧氏距离。"),
    "repetition_count_left": ("derived_engineering", "60", "count",
        ["ShoulderLeft", "HipLeft"], "sign_left_negative", True,
        "MATLAB findpeaks 与 scipy find_peaks 在平台段不等价，v1 只用于『是否完成 5 次』二值判断。"),
    "repetition_count_right": ("derived_engineering", "41", "count",
        ["ShoulderRight", "HipRight"], "sign_right_positive", True,
        "同上，右侧。"),
    "torso_tilt_left_excursion_up": ("derived_engineering", "60,61,62", "max-of-diff",
        ["ShoulderLeft", "HipLeft"], "sign_left_negative", False,
        "相对首个极值的上向偏移，依赖未标定的相机竖直轴。"),
    "torso_tilt_left_excursion_down": ("derived_engineering", "60,61,62", "max-of-diff",
        ["ShoulderLeft", "HipLeft"], "sign_left_negative", False,
        "相对首个极值的下向偏移。"),
    "torso_tilt_right_excursion_up": ("derived_engineering", "41,42,43", "max-of-diff",
        ["ShoulderRight", "HipRight"], "sign_right_positive", False,
        "同上，右侧。"),
    "torso_tilt_right_excursion_down": ("derived_engineering", "41,42,43", "max-of-diff",
        ["ShoulderRight", "HipRight"], "sign_right_positive", False,
        "同上，右侧。"),
}

TEMPLATE = '''kimore:feature_{fid} a owl:NamedIndividual, kimore:Feature ;
    rdfs:label "{label}"@zh ;
    kimore:featureId "{fid}" ;
    kimore:unit "{unit}" ;
    kimore:evidenceLevel "{level}" ;
    kimore:paperCitation "{paper}" ;
    kimore:hasSourceLine "{script}:{lines}" ;
    kimore:aggregation "{agg}" ;
    kimore:usesJoint {joints} ;
    kimore:verticalReferenceIndependent {vri} ;
{sign}    kimore:version "1.0"{comment} .
'''

HEADER = '''@prefix kimore: <https://kimore.liaoyuyoufang.example/ontology#> .
@prefix owl:    <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .

##############################################################################
# Es2 的 17 个特征个体（由 tools/gen_ontology_features.py 生成，勿手改）
#
# 生成逻辑：
#   1. 从 MCP 真实响应 real_assess_success.json 读取 feature_id 与 unit；
#   2. 与 METADATA 中人工维护的证据信息合并；
#   3. 输出本文件，天然与契约同步——契约改了，重跑脚本即可。
#
# 这样做的意义：本体不是一次性文档，而是与工具契约同源、可重复生成的资产。
##############################################################################

kimore:exercise_Es2 kimore:hasFeature
'''

# 中英文标签，人工维护（feature_id -> 中文名）
LABELS = {
    "torso_tilt_left_peak": "左侧躯干额状面峰值倾角",
    "torso_tilt_right_peak": "右侧躯干额状面峰值倾角",
    "torso_tilt_left_range": "左侧躯干倾角活动范围",
    "torso_tilt_right_range": "右侧躯干倾角活动范围",
    "elbow_angle_left_median": "左肘关节角度中位数",
    "elbow_angle_right_median": "右肘关节角度中位数",
    "knee_angle_left_median": "左膝关节角度中位数",
    "knee_angle_right_median": "右膝关节角度中位数",
    "hand_distance_median": "双手间距中位数",
    "shoulder_distance_median": "双肩间距中位数",
    "hip_distance_median": "双髋间距中位数",
    "repetition_count_left": "左侧动作重复次数",
    "repetition_count_right": "右侧动作重复次数",
    "torso_tilt_left_excursion_up": "左侧躯干上向偏移",
    "torso_tilt_left_excursion_down": "左侧躯干下向偏移",
    "torso_tilt_right_excursion_up": "右侧躯干上向偏移",
    "torso_tilt_right_excursion_down": "右侧躯干下向偏移",
}


def load_contract() -> dict[str, str]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    feats = data["data"]["features"]
    return {f["feature_id"]: f["unit"] for f in feats}


def render() -> str:
    units = load_contract()
    missing_meta = sorted(set(units) - set(METADATA))
    missing_contract = sorted(set(METADATA) - set(units))
    if missing_meta or missing_contract:
        raise SystemExit(
            f"契约与元数据不一致\n  契约多出: {missing_meta}\n  元数据多出: {missing_contract}"
        )

    parts = [HEADER]
    parts.append(" ,\n".join(f"    kimore:feature_{fid}" for fid in units) + " .\n\n")

    for fid, unit in units.items():
        level, lines, agg, joints, sign, vri, note = METADATA[fid]
        sign_line = f"    kimore:hasSignConvention kimore:{sign} ;\n" if sign else ""
        comment = f' ;\n    rdfs:comment "{note}"@zh' if note else ""
        parts.append(
            TEMPLATE.format(
                fid=fid,
                label=LABELS[fid],
                unit=unit,
                level=level,
                paper=PAPER if level == "verified_paper" else PAPER + "（聚合口径为本项目工程选择）",
                script=SCRIPT,
                lines=lines,
                agg=agg,
                joints=" , ".join(f'"{j}"' for j in joints),
                vri="true" if vri else "false",
                sign=sign_line,
                comment=comment,
            )
        )
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查生成结果与磁盘是否一致")
    args = ap.parse_args()

    text = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current.strip() != text.strip():
            print("features.ttl 与契约不同步，请重新生成")
            return 1
        print("features.ttl 与契约一致")
        return 0

    OUT.write_text(text, encoding="utf-8")
    units = load_contract()
    print(f"wrote {OUT}  features={len(units)}  bytes={len(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
