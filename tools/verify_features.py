# -*- coding: utf-8 -*-
"""用作者 feat_extract_Ex2.m 的原始流程复算 Es2 特征，核对 B 给出的数值。"""
import io
import json
import re
import zipfile
from collections import defaultdict

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

ZIP = r"E:\study\3u\ICT\reference\archive.zip"
OUT = r"F:\deepseek-harness\华为ICT\tools\verify_b_features.json"
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


def read_jp(z, name):
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


def joint(arr, key):
    i = IDX[key] - 1
    return arr[:, i:i + 3]


def filtering(x):
    b, a = butter(3, (2 * 1.0) / 30.0, "low")
    return filtfilt(b, a, x)


def torso_tilt(jp, side):
    sh = joint(jp, f"Shoulder_{side}")
    hip = joint(jp, f"Hip_{side}")
    ang = np.degrees(np.arctan2(sh[:, 0] - hip[:, 0], sh[:, 1] - hip[:, 1]))
    ang = -filtering(ang)          # 作者对 PO 取负
    ang = ang[29:]                 # 作者丢弃前 30 帧
    return ang


def peaks_of(ang):
    n = len(ang)
    hi, _ = find_peaks(ang, height=float(np.mean(ang)), distance=max(1, n // 10))
    inv = float(np.max(ang)) - ang
    lo, _ = find_peaks(inv, height=float(np.mean(inv)), distance=max(1, n // 8))
    vals_lo = float(np.max(ang)) - inv[lo]
    return hi, vals_lo


def angle3(a, b, c):
    """b 为顶点，返回角度（度）"""
    ba = a - b
    bc = c - b
    cos = np.sum(ba * bc, axis=1) / (np.linalg.norm(ba, axis=1) * np.linalg.norm(bc, axis=1))
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


res = {"candidates": [], "match": None}

with zipfile.ZipFile(ZIP) as z:
    jp_names = [n for n in z.namelist() if "JointPosition" in n and n.lower().endswith(".csv")]
    es2 = []
    for n in jp_names:
        m = PAT.search(n)
        if not m or m.group(4) != "Es2":
            continue
        es2.append((m.group(2), m.group(3), n))

    # 先按行数快速筛
    cands = []
    for grp, sid, n in es2:
        raw = z.read(n)
        cnt = sum(1 for line in raw.split(b"\n") if line.strip())
        cands.append({"group": grp, "subject": sid, "file": n, "lines": cnt})
    res["all_es2"] = cands
    targets = [c for c in cands if c["lines"] in (1664, 1665, 1666) and c["group"] == "Expert"]
    res["targets_1664_expert"] = targets

    for t in targets:
        jp = read_jp(z, t["file"])
        t["shape"] = list(jp.shape)
        out = {}
        for side, key in (("L", "torso_tilt_left"), ("R", "torso_tilt_right")):
            ang = torso_tilt(jp, "Left" if side == "L" else "Right")
            hi_idx, lo_vals = peaks_of(ang)
            out[key + "_peak_min"] = float(np.min(lo_vals)) if len(lo_vals) else None
            out[key + "_peak_max"] = float(np.max(ang[hi_idx])) if len(hi_idx) else None
            out[key + "_range"] = (float(np.max(ang) - np.min(ang)))
            out[key + "_n_peaks"] = int(len(hi_idx))
            out[key + "_first5"] = [round(float(v), 3) for v in ang[:5]]
        # CF: 截掉尾部 15 帧后滤波
        def trim_cf(x):
            return filtering(x[:-15])
        el = angle3(joint(jp, "Shoulder_Left"), joint(jp, "Elbow_Left"), joint(jp, "Wrist_Left"))
        kn = angle3(joint(jp, "Hip_Left"), joint(jp, "Knee_Left"), joint(jp, "Ankle_Left"))
        out["elbow_angle_left_median"] = float(np.median(trim_cf(el)))
        out["knee_angle_left_median"] = float(np.median(trim_cf(kn)))
        sh_d = np.linalg.norm(joint(jp, "Shoulder_Left") - joint(jp, "Shoulder_Right"), axis=1)
        out["shoulder_distance_median"] = float(np.median(trim_cf(sh_d)))
        t["computed"] = out
        res["candidates"].append(t)

# 与 B 的数值比对
B = {
    "torso_tilt_left_peak": -26.497, "torso_tilt_right_peak": 20.901,
    "torso_tilt_left_range": 37.489, "torso_tilt_right_range": 32.478,
    "elbow_angle_left_median": 164.214, "knee_angle_left_median": 166.161,
    "shoulder_distance_median": 0.283, "repetition_count_left": 6,
}
if res["candidates"]:
    c = res["candidates"][0]
    got = c["computed"]
    cmp_rows = []
    for k, v in B.items():
        if k == "torso_tilt_left_peak":
            g = got.get("torso_tilt_left_peak_min")
        elif k == "torso_tilt_right_peak":
            g = got.get("torso_tilt_right_peak_max")
        elif k == "torso_tilt_left_range":
            g = got.get("torso_tilt_left_range")
        elif k == "torso_tilt_right_range":
            g = got.get("torso_tilt_right_range")
        elif k == "repetition_count_left":
            g = got.get("torso_tilt_left_n_peaks")
        else:
            g = got.get(k)
        cmp_rows.append({"feature": k, "b_value": v, "recomputed": g,
                         "diff": None if g is None else round(float(g) - v, 3)})
    res["match"] = cmp_rows

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("saved:", OUT)
print("targets:", res["targets_1664_expert"])
print(json.dumps(res["match"], ensure_ascii=False, indent=2))
