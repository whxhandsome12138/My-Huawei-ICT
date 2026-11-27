# -*- coding: utf-8 -*-
"""按作者 feat_extract_Ex2.m 的原始流程复算 Es2 特征，核对服务端给出的数值。

与 B 讨论后（2026-11-27）修正的一处关键事实：
    作者对**左侧**信号取负（feat_extract_Ex2.m:26），右侧**不**取负（:27）。
    本脚本早先版本对两侧都取负，导致左侧峰值反号 —— 已修正。

运行：
    python verify_features.py                 # 默认样本 E_ID1/Es2
    python verify_features.py --csv out.json  # 另存结果

依赖：numpy, scipy。数据从 archive.zip 直接读，不需要解压。
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

ZIP = r"E:\study\3u\ICT\reference\archive.zip"
PAT = re.compile(r"Kimore/(CG|GPP)/([^/]+)/([^/]+)/(Es[1-5])/")

# 关节列索引（与作者 preproc_Ex2.m 一致：1-based，每关节 4 列 xyzt）
IDX = {
    "Spine_Base": 1, "Spine_Mid": 5, "Neck": 9, "Head": 13,
    "Shoulder_Left": 17, "Elbow_Left": 21, "Wrist_Left": 25, "Hand_Left": 29,
    "Shoulder_Right": 33, "Elbow_Right": 37, "Wrist_Right": 41, "Hand_Right": 45,
    "Hip_Left": 49, "Knee_Left": 53, "Ankle_Left": 57, "Foot_Left": 61,
    "Hip_Right": 65, "Knee_Right": 69, "Ankle_Right": 73, "Foot_Right": 77,
    "Spine_Shoulder": 81, "Tip_Left": 85, "Thumb_Left": 89,
    "Tip_Right": 93, "Thumb_Right": 97,
}


def read_jp(z: zipfile.ZipFile, name: str) -> np.ndarray:
    raw = z.read(name).decode("utf-8", "ignore")
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 100:
            continue
        try:
            rows.append([float(p) if p.strip() else np.nan for p in parts[:100]])
        except ValueError:
            continue
    return np.array(rows, dtype=float)


def joint(arr: np.ndarray, key: str) -> np.ndarray:
    i = IDX[key] - 1
    return arr[:, i:i + 3]


def filtering(x: np.ndarray) -> np.ndarray:
    """filtering.m：3 阶 Butterworth，截止 1 Hz，采样 30 Hz，filtfilt 零相位。"""
    b, a = butter(3, (2 * 1.0) / 30.0, "low")
    return filtfilt(b, a, x)


def torso_tilt(jp: np.ndarray, side: str) -> np.ndarray:
    """作者流程：atan2 → 滤波 → 左侧取负（:26）、右侧不取（:27）→ 丢前 29 帧（:29-30）。"""
    sh = joint(jp, f"Shoulder_{side}")
    hip = joint(jp, f"Hip_{side}")
    ang = np.degrees(np.arctan2(sh[:, 0] - hip[:, 0], sh[:, 1] - hip[:, 1]))
    ang = filtering(ang)
    if side == "Left":
        ang = -ang          # feat_extract_Ex2.m:26 —— 只有左侧
    return ang[29:]         # MATLAB x(30:end)


def peaks_of(ang: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """峰：height=mean、distance=⌊n/10⌋；谷：对 max(x)-x 找峰、distance=⌊n/8⌋。"""
    n = len(ang)
    hi, _ = find_peaks(ang, height=float(np.mean(ang)), distance=max(1, n // 10))
    inv = float(np.max(ang)) - ang
    lo, _ = find_peaks(inv, height=float(np.mean(inv)), distance=max(1, n // 8))
    return hi, float(np.max(ang)) - inv[lo]


def angle3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """b 为顶点，返回角度（度）——作者用余弦定理。"""
    ba = a - b
    bc = c - b
    cos = np.sum(ba * bc, axis=1) / (np.linalg.norm(ba, axis=1) * np.linalg.norm(bc, axis=1))
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="verify_features.json", help="结果写到哪里")
    ap.add_argument("--lines", type=int, default=1664, help="目标录制行数")
    args = ap.parse_args()

    out: dict = {"sample": None, "features": {}, "notes": []}

    with zipfile.ZipFile(ZIP) as z:
        cand = None
        for n in z.namelist():
            if "JointPosition" not in n or not n.lower().endswith(".csv"):
                continue
            m = PAT.search(n)
            if not m or m.group(4) != "Es2" or m.group(2) != "Expert":
                continue
            lines = sum(1 for line in z.read(n).split(b"\n") if line.strip())
            if abs(lines - args.lines) <= 2:
                cand = (m.group(2), m.group(3), n, lines)
                break
        if not cand:
            raise SystemExit(f"没找到 {args.lines} 行的 Expert/Es2 录制")

        grp, sid, name, lines = cand
        jp = read_jp(z, name)
        out["sample"] = {"group": grp, "subject": sid, "file": name, "shape": list(jp.shape)}

        feats: dict = {}
        for side, key in (("Left", "left"), ("Right", "right")):
            ang = torso_tilt(jp, side)
            hi_idx, lo_vals = peaks_of(ang)
            feats[f"torso_tilt_{key}_peak"] = {
                "value": round(float(np.max(ang)), 3),
                "definition": "每次重复极大值中的最大者（PO 向量取最大）",
                "peak_frame": int(hi_idx[np.argmax(ang[hi_idx])]) if len(hi_idx) else None,
                "n_peaks": int(len(hi_idx)),
                "n_troughs": int(len(lo_vals)),
                "min": round(float(np.min(ang)), 3),
                "max": round(float(np.max(ang)), 3),
            }
            feats[f"torso_tilt_{key}_range"] = round(float(np.max(ang) - np.min(ang)), 3)

        def trim_cf(x: np.ndarray) -> np.ndarray:
            return filtering(x[:-15])       # 作者 (1:end-15)

        el = angle3(joint(jp, "Shoulder_Left"), joint(jp, "Elbow_Left"), joint(jp, "Wrist_Left"))
        kn = angle3(joint(jp, "Hip_Left"), joint(jp, "Knee_Left"), joint(jp, "Ankle_Left"))
        sh_d = np.linalg.norm(joint(jp, "Shoulder_Left") - joint(jp, "Shoulder_Right"), axis=1)
        feats["elbow_angle_left_median"] = round(float(np.median(trim_cf(el))), 3)
        feats["knee_angle_left_median"] = round(float(np.median(trim_cf(kn))), 3)
        feats["shoulder_distance_median"] = round(float(np.median(trim_cf(sh_d))), 4)

        # 相机几何观察：右肩 x − 左肩 x
        dx = float(np.median(joint(jp, "Shoulder_Right")[:, 0] - joint(jp, "Shoulder_Left")[:, 0]))
        out["shoulder_right_minus_left_x"] = round(dx, 4)

        out["features"] = feats
        out["notes"] = [
            "左侧取负、右侧不取负（feat_extract_Ex2.m:26-27）；两侧正值都表示向该侧偏离。",
            "两份信号整体存在约 +18° 的相机几何偏置，绝对角度不宜直接当'偏离竖直轴多少度'念。",
        ]

    with open(args.csv, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    f = out["features"]
    print(f"sample: {out['sample']['group']}/{out['sample']['subject']}  shape={out['sample']['shape']}")
    print(f"  left_peak  = {f['torso_tilt_left_peak']['value']:>8}  "
          f"(min {f['torso_tilt_left_peak']['min']}, max {f['torso_tilt_left_peak']['max']}, "
          f"peaks {f['torso_tilt_left_peak']['n_peaks']}, troughs {f['torso_tilt_left_peak']['n_troughs']})")
    print(f"  right_peak = {f['torso_tilt_right_peak']['value']:>8}  "
          f"(min {f['torso_tilt_right_peak']['min']}, max {f['torso_tilt_right_peak']['max']}, "
          f"peaks {f['torso_tilt_right_peak']['n_peaks']}, troughs {f['torso_tilt_right_peak']['n_troughs']})")
    print(f"  left_range = {f['torso_tilt_left_range']}, right_range = {f['torso_tilt_right_range']}")
    print(f"  elbow={f['elbow_angle_left_median']}  knee={f['knee_angle_left_median']}  "
          f"shoulder_dist={f['shoulder_distance_median']}")
    print(f"saved: {args.csv}")


if __name__ == "__main__":
    main()
