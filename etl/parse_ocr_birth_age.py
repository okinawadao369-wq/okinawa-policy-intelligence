#!/usr/bin/env python3
"""OCR（tesseract jpn, psm 6）した出生第3表テキストを tidy CSV 化。
画像PDFのみで公表された年（2022年）用。3重の整合性QA（総数=男+女／年齢計=総数／市町村計=県総数）を全て通った場合のみ書き出す。"""
import re, sys, csv
pages, year, out, names_csv = sys.argv[1:4], sys.argv[4], sys.argv[5], sys.argv[6]
GROUPS = [["総数","14歳以下","15-19歳","20-24歳"],["25-29歳","30-34歳","35-39歳","40-44歳"],["45-49歳"]]
names = [r["name_ja"] for r in csv.DictReader(open(names_csv, encoding="utf-8"))] + ["総数","市部","郡部","不詳"]
def num(t):
    if re.fullmatch(r"[ー\-—–‐]+", t): return 0
    t = t.replace(".", "").replace(",", "")
    return int(t) if t.isdigit() else None
OCR_NAME_FIX = {"渡名豆村": "渡名喜村"}  # OCRの文字誤認（画像で確認済み）
recs, errs = {}, []
for gi, p in enumerate(pages):
    for ln in open(p, encoding="utf-8"):
        ln = ln.replace("。", " ").replace("|", " ").strip()
        tok = ln.split()
        if tok: tok[0] = OCR_NAME_FIX.get(tok[0], tok[0])
        if not tok or tok[0] not in names + [n for n in [] ]: 
            if tok and tok[0].endswith("保健所"): pass
            else: continue
        vals = [num(t) for t in tok[1:]]
        vals = [v for v in vals if v is not None]
        need = 3 * len(GROUPS[gi])
        if len(vals) != need: errs.append(f"p{gi} {tok[0]}: {len(vals)} values"); continue
        for i, g in enumerate(GROUPS[gi]):
            t, m, f = vals[3*i:3*i+3]
            if t != m + f: errs.append(f"{tok[0]} {g}: {t}!={m}+{f}")
            recs.setdefault(tok[0], {})[g] = t
ZERO_COLS = ["50歳以上","不詳"]  # 2022年版は全行「－」を目視確認（docs/DECISIONS.md D-003）
for d in recs.values():
    for z in ZERO_COLS: d.setdefault(z, 0)
for n, d in recs.items():
    if len(d) == 11 and sum(v for k, v in d.items() if k != "総数") != d["総数"]: errs.append(f"{n}: 年齢計≠総数")
munis = [n for n in names[:-4]]
missing = [n for n in munis if n not in recs or len(recs[n]) != 11]
if missing: errs.append(f"missing {missing}")
elif sum(recs[n]["総数"] for n in munis) != recs["総数"]["総数"]: errs.append("市町村計≠県総数")
for g in ["15-19歳","20-24歳","25-29歳","30-34歳","35-39歳","40-44歳"]:
    if not missing and sum(recs[n][g] for n in munis) != recs["総数"][g]: errs.append(f"列 {g}: 市町村計≠県計")
if errs: print("QA FAILED", errs); sys.exit(1)
w = csv.writer(open(out, "w", newline="", encoding="utf-8")); w.writerow(["year","muni_name","age_group","births","source_table"])
for n, d in recs.items():
    for k, v in d.items(): w.writerow([year, n, k, v, "沖縄県衛生統計年報(人口動態編) 出生第3表 [OCR]"])
print(f"QA passed: units={len(recs)}")
