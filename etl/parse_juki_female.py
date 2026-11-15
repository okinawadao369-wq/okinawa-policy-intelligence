#!/usr/bin/env python3
"""総務省「住民基本台帳年齢階級別人口（市区町村別）【日本人住民】」から沖縄41市町村の女性・年齢5歳階級人口を抽出。
基準日: 各年1月1日。QA: 41市町村の合計 == 沖縄県計（各年齢階級）、性別 計=男+女。"""
import sys, csv, re
files, out, names_csv = sys.argv[1:-2], sys.argv[-2], sys.argv[-1]
munis = {r["lg_code6"]: r for r in csv.DictReader(open(names_csv, encoding="utf-8"))}
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]  # 表記ゆれ（歳の有無）を吸収
def rows_of(path):
    if path.endswith(".xls"):
        import xlrd; sh = xlrd.open_workbook(path).sheet_by_index(0)
        return [sh.row_values(i) for i in range(sh.nrows)]
    import openpyxl; return [list(r) for r in openpyxl.load_workbook(path, read_only=True).worksheets[0].iter_rows(values_only=True)]
norm = lambda s: re.sub(r"[～〜~]", "-", str(s or "")).replace(" ", "").replace("　", "").replace("歳", "")
w = csv.writer(open(out, "w", newline="", encoding="utf-8"))
w.writerow(["ref_date", "muni_code5", "lg_code6", "name_ja", "age_group", "female_japanese", "source_file"])
for path in files:
    year = re.search(r"(\d{4})", path.split("/")[-1]).group(1)
    rows = rows_of(path)
    hdr = next(r for r in rows if any(norm(c) == "15-19" for c in r))
    col = {a: next(i for i, c in enumerate(hdr) if norm(c) == a) for a in AGES}
    tot_col = next(i for i, c in enumerate(hdr) if norm(c) == "総数")
    data, pref = {}, None
    for r in rows:
        code = str(r[0]).strip().split(".")[0].zfill(6) if r[0] not in (None, "") else ""
        sex = norm(r[3]) if len(r) > 3 else ""
        if not code.startswith("47"): continue
        vals = {a: int(float(r[col[a]])) for a in AGES}
        if code == "470007":
            pref = pref or {}; pref[sex] = vals
        elif code in munis:
            data.setdefault(code, {})[sex] = vals
    errs = []
    if set(data) != set(munis): errs.append(f"missing {set(munis) - set(data)}")
    for a in AGES:
        s = sum(d["女"][a] for d in data.values())
        if s != pref["女"][a]: errs.append(f"{a}: 41計{s}≠県{pref['女'][a]}")
        for c, d in data.items():
            if d["計"][a] != d["男"][a] + d["女"][a]: errs.append(f"{c} {a} 計≠男+女")
    print(year, "OK" if not errs else "QA FAILED", errs[:3], "県女性15-49:", sum(pref["女"].values()))
    if errs: sys.exit(1)
    for c, d in sorted(data.items()):
        for a in AGES:
            w.writerow([f"{year}-01-01", c[:5], c, munis[c]["name_ja"], a + "歳", d["女"][a], path.split("/")[-1]])
