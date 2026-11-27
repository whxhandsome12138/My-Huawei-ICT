# -*- coding: utf-8 -*-
"""核对 KIMORE 临床评分表（ClinicalAssessment_*.xlsx）到底有多少有效标签。

为什么要有这个脚本：
    交接时出现过三个不同的数（77 人 391 段 / 80 段 / 76 段），
    争论的根源是"谁算有效"没有统一判据。这里把判据写死成四条，
    然后给出可复现的明细，避免再靠记忆对账。

判据（同时满足才算有效）：
    1. A2（受试者 ID）与所在目录名一致
    2. cTS ∈ [10, 50]、cPO ∈ [3, 15]、cCF ∈ [7, 35]（量表区间）
    3. cTS == cPO + cCF（数据集自洽关系，误差 < 1e-6）
    4. 三个分都不是空单元格

用法：
    python label_audit.py                 # 打印汇总 + 无效明细
    python label_audit.py --json out.json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from collections import Counter, defaultdict

from openpyxl import load_workbook

ZIP = r"E:\study\3u\ICT\reference\archive.zip"
PAT = re.compile(r"Kimore/(CG|GPP)/([^/]+)/([^/]+)/(Es[1-5])/Label/ClinicalAssessment_([^/]+)\.xlsx$")


def cell(ws, ref):
    v = ws[ref].value
    if isinstance(v, str):
        v = v.strip()
        try:
            return float(v)
        except ValueError:
            return None
    return float(v) if isinstance(v, (int, float)) else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="label_audit.json")
    args = ap.parse_args()

    rows = []
    with zipfile.ZipFile(ZIP) as z:
        names = [n for n in z.namelist() if "ClinicalAssessment_" in n and n.endswith(".xlsx")]
        for n in names:
            m = PAT.search(n)
            if not m:
                continue
            grp, subject, ex, fname_id = m.group(2), m.group(3), m.group(4), m.group(5)
            with z.open(n) as fh:
                wb = load_workbook(io.BytesIO(fh.read()), data_only=True, read_only=True)
                ws = wb["Foglio1"] if "Foglio1" in wb.sheetnames else wb.worksheets[0]
                a2 = ws["A2"].value
                a2 = str(a2).strip() if a2 is not None else ""
                ts, po, cf = cell(ws, "C2"), cell(ws, "H2"), cell(ws, "M2")
                wb.close()

            reasons = []
            if a2 != subject:
                reasons.append(f"ID 不符（表内 {a2 or '空'}）")
            if ts is None or po is None or cf is None:
                reasons.append("有空单元格")
            else:
                if not (10 <= ts <= 50):
                    reasons.append(f"cTS 越界 {ts}")
                if not (3 <= po <= 15):
                    reasons.append(f"cPO 越界 {po}")
                if not (7 <= cf <= 35):
                    reasons.append(f"cCF 越界 {cf}")
                if abs(ts - (po + cf)) > 1e-6:
                    reasons.append(f"cTS≠cPO+cCF（{ts} vs {round(po + cf, 3)}）")

            rows.append({
                "group": grp, "subject": subject, "exercise": ex,
                "file_id": fname_id, "cTS": ts, "cPO": po, "cCF": cf,
                "valid": not reasons, "reasons": reasons,
            })

    total = len(rows)
    valid = [r for r in rows if r["valid"]]
    invalid = [r for r in rows if not r["valid"]]
    subs_all = sorted({r["subject"] for r in rows})
    subs_valid = sorted({r["subject"] for r in valid})
    by_subject = defaultdict(set)
    for r in valid:
        by_subject[r["subject"]].add(r["exercise"])
    five = [s for s, ex in by_subject.items() if len(ex) == 5]
    one = [s for s, ex in by_subject.items() if len(ex) >= 1]

    summary = {
        "workbooks": total,
        "subjects_total": len(subs_all),
        "valid_combos": len(valid),
        "subjects_with_valid": len(subs_valid),
        "subjects_all_five": len(five),
        "subjects_at_least_one": len(one),
        "invalid_combos": len(invalid),
        "invalid_by_subject": dict(Counter(r["subject"] for r in invalid)),
        "valid_by_group": dict(Counter(r["group"] for r in valid)),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n无效组合明细：")
    for r in sorted(invalid, key=lambda x: (x["subject"], x["exercise"])):
        print(f"  {r['subject']:>8} {r['exercise']}  {'; '.join(r['reasons'])}")

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {args.json}")


if __name__ == "__main__":
    main()
