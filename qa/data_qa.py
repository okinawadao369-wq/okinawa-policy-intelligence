"""Data QA: 市町村コード・検査数字・パイロット出生データの整合性。失敗時は終了コード1。"""
import csv, sqlite3, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
errs = []
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
db = sqlite3.connect(":memory:"); db.executescript(open(root / "docs/schema.sql", encoding="utf-8").read())
print("\n".join(errs) or "Data QA passed"); sys.exit(1 if errs else 0)
