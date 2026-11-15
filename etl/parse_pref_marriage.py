#!/usr/bin/env python3
"""沖縄県衛生統計年報 婚姻 第1表（婚姻件数×市町村、夫妻の初婚-再婚）→ tidy CSV。
取得列: 総数（婚姻件数）と 夫初婚・妻初婚（夫妻とも初婚）。QA: 41市町村計 == 県総数。"""
import sys, csv, re
src, year, out, names_csv = sys.argv[1:5]
names = [r["name_ja"] for r in csv.DictReader(open(names_csv, encoding="utf-8"))]
txt = open(src, encoding="utf-8").read()
i = txt.find("婚姻 第１表"); j = txt.find("婚姻 第２表", i)
if i < 0: print("table not found"); sys.exit(2)
block = txt[i: j if j > 0 else None]
num = lambda t: 0 if re.fullmatch(r"[-－ー]+", t) else int(t.replace(",", ""))
rec = {}
for ln in block.split("\n"):
    tok = ln.split()
    if len(tok) >= 3 and (tok[0] in names or tok[0] == "総数") and tok[0] not in rec:
        try:
            v = [num(t) for t in tok[1:8]]
            if v[0] != v[1] + v[2] + v[5] + v[6]: print("row QA fail", tok[0], v); continue  # 総数=夫初婚(妻初婚+妻再婚)+夫再婚(妻初婚+妻再婚)
            rec[tok[0]] = (v[0], v[1])
        except (ValueError, IndexError): pass
miss = [n for n in names if n not in rec]
s = sum(rec[n][0] for n in names if n in rec)
s1 = sum(rec[n][1] for n in names if n in rec)
ok = not miss and s == rec.get("総数", (None,))[0] and s1 == rec["総数"][1]
print(year, "munis", len(names) - len(miss), "sum", s, "県総数", rec.get("総数"), "missing", miss, "OK" if ok else "QA FAILED")
if not ok: sys.exit(1)
w = csv.writer(open(out, "w", newline="", encoding="utf-8")); w.writerow(["year", "muni_name", "marriages_total", "marriages_both_first", "source_table"])
for n in names + ["総数"]: w.writerow([year, n, rec[n][0], rec[n][1], "沖縄県衛生統計年報(人口動態編) 婚姻第1表"])
