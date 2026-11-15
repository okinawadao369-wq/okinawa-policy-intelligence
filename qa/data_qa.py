"""Data QA: 市町村コード・検査数字・パイロット出生データの整合性。失敗時は終了コード1。"""
import csv, sqlite3, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
errs, warns = [], []
munis = list(csv.DictReader(open(root / "data/municipalities.csv", encoding="utf-8")))
if len(munis) != 41: errs.append(f"市町村数 {len(munis)} != 41")
for m in munis:
    c = m["muni_code5"]; s = sum(int(d) * w for d, w in zip(c, [6, 5, 4, 3, 2])); r = s % 11
    if m["lg_code6"] != c + str((11 - r) % 10 if r else 1): errs.append(f"検査数字不一致 {c}")
codes = {m["muni_code5"] for m in munis}
rows = list(csv.DictReader(open(root / "data/pilot_births_by_mother_age_2024.csv", encoding="utf-8")))
by = {}
for r in rows:
    if r["muni_code5"] not in codes: errs.append(f"未知コード {r['muni_code5']}")
    by.setdefault(r["muni_code5"], {})[r["age_group"]] = int(r["births"])
for c, d in by.items():
    if sum(v for k, v in d.items() if k != "総数") != d["総数"]: errs.append(f"年齢合計≠総数 {c}")
if sum(d["総数"] for d in by.values()) != 11753: errs.append("41市町村計が県総数11,753と不一致")
# W1: 2015-2024 出生×母の年齢、婚姻、住基女性
from collections import defaultdict
bt = defaultdict(int); pref = {}
for r in csv.DictReader(open(root / "data/births_by_mother_age.csv", encoding="utf-8")):
    if r["age_group"] != "総数": continue
    if r["muni_code5"] == "47000": pref[r["year"]] = int(r["births"])
    elif r["muni_code5"] in codes: bt[r["year"]] += int(r["births"])
    else: errs.append(f"births 未知コード {r['muni_code5']}")
if sorted(pref) != [str(y) for y in range(2015, 2025)]: errs.append(f"births 年欠損 {sorted(pref)}")
for y, v in pref.items():
    if bt[y] != v: errs.append(f"births {y}: 41市町村計{bt[y]}≠県{v}")
mt = defaultdict(int); mp = {}
for r in csv.DictReader(open(root / "data/marriages.csv", encoding="utf-8")):
    if r["muni_code5"] == "47000": mp[r["year"]] = int(r["marriages_total"])
    else: mt[r["year"]] += int(r["marriages_total"])
for y, v in mp.items():
    if mt[y] != v: errs.append(f"marriages {y}: 41市町村計≠県")
jk = defaultdict(set)
for r in csv.DictReader(open(root / "data/juki_female_japanese.csv", encoding="utf-8")):
    jk[r["ref_date"][:4]].add(r["muni_code5"])
    v = int(r["female_japanese"])
    if v < 0: errs.append(f"juki 負の値 {r['muni_code5']} {r['ref_date']} {r['age_group']}")
    elif v == 0: warns.append(f"juki 分母0（年齢別出生率は未定義・5年プールで扱う）{r['muni_code5']} {r['ref_date']} {r['age_group']}")
for y in range(2015, 2027):
    if jk[str(y)] != codes: errs.append(f"juki {y}: 市町村欠損")
db = sqlite3.connect(":memory:"); db.executescript(open(root / "docs/schema.sql", encoding="utf-8").read())
print("\n".join("WARN " + w for w in warns)); print("\n".join(errs) or "Data QA passed"); sys.exit(1 if errs else 0)
