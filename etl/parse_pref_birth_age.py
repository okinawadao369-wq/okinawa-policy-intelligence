#!/usr/bin/env python3
"""沖縄県衛生統計年報(人口動態編) 出生 第3表（母の年齢5歳階級×市町村）PDFテキストを tidy CSV 化。
入力: pdftotext -layout 済みテキスト。出力: muni_name, age_group, births（総数のみ）。
'-' は 0（計数のない場合）として扱う。QA: 各市町村の年齢合計 == 総数 を検査。"""
import re, sys, csv
src, year, out = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src, encoding="utf-8").read().split("\n")
blocks, cur = [], None
for ln in lines:
    if "出生 第３表" in ln:
        cur = {"groups": None, "rows": []}; blocks.append(cur); continue
    if cur is None: continue
    if cur["groups"] is None and "保 健 所" in ln:
        g = re.findall(r"(総数|１４歳以下|[０-９]+～[０-９]+歳|５０歳以上|不詳)", ln)
        cur["groups"] = g; continue
    if "出生 第４表" in ln: cur = None; continue
    m = re.match(r"^\s*([^\s\d\-]+?)\s+([\d,\-].*)$", ln)
    if m and cur["groups"]:
        name = m.group(1).strip()
        if name in ("市", "町", "村") or "市 町 村" in ln: continue
        vals = m.group(2).split()
        cur["rows"].append((name, vals))
recs = {}
for b in blocks:
    if not b["groups"]: continue
    for name, vals in b["rows"]:
        for i, g in enumerate(b["groups"]):
            if 3*i < len(vals):
                v = vals[3*i]; v = 0 if v == "-" else int(v.replace(",", ""))
                recs.setdefault(name, {})[g] = v
z2h = str.maketrans("０１２３４５６７８９～", "0123456789-")
w = csv.writer(open(out, "w", newline="", encoding="utf-8"))
w.writerow(["year", "muni_name", "age_group", "births", "source_table"])
bad = []
for name, d in recs.items():
    parts = sum(v for k, v in d.items() if k != "総数")
    if d.get("総数") is not None and parts != d["総数"]: bad.append((name, d.get("総数"), parts))
    for k, v in d.items():
        w.writerow([year, name, k.translate(z2h), v, "沖縄県衛生統計年報(人口動態編) 出生第3表"])
print(f"units={len(recs)} qa_sum_mismatch={bad}")
