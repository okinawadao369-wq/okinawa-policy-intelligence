#!/usr/bin/env python3
"""沖縄県衛生統計年報（人口動態編）人口動態統計指標「出生 第４表
出生数，性，母の年齢（５歳階級），出生順位，出生当時の世帯の主な仕事別」（県全体）を tidy CSV 化する。

入力: 年ごとの pdftotext -layout 出力（テキストPDFの年）または OCR テキスト（2022年）。
QA（全て通過した年のみ出力）:
  1) 各セル 総数 = 男 + 女
  2) 出生順位計（第1子..第5子以上+不詳） = 総数
  3) 母の年齢計 = 年齢「総数」行
  4) 世帯の主な仕事 7区分の計 = （総数）ブロック
使い方: parse_pref_birth_order.py <year> <text_file> <out_csv> [extraction]
"""
import re, sys, csv, unicodedata

year, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
extraction = sys.argv[4] if len(sys.argv) > 4 else "pdftotext"
ORDERS_A = ["総数", "第1子", "第2子", "第3子"]
ORDERS_B = ["第4子", "第5子以上", "不詳"]
AGES = ["総数", "14歳以下", "15-19歳", "20-24歳", "25-29歳", "30-34歳", "35-39歳",
        "40-44歳", "45-49歳", "50歳以上", "不詳"]
HH = ["総数", "農家世帯", "自営業者世帯", "常用勤労者世帯Ⅰ", "常用勤労者世帯Ⅱ", "その他の世帯", "無職の世帯", "不詳"]


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return s.replace("～", "-").replace("~", "-").replace("〜", "-")


def num(t):
    t = t.replace(",", "").replace(".", "")
    if re.fullmatch(r"[-ー—–‐]+", t):
        return 0
    return int(t) if t.isdigit() else None


HH_N = {norm(h): h for h in HH}
AGE_N = {norm(a.replace("-", "～")): a for a in AGES}
AGE_N.update({a: a for a in AGES})

data = {}  # (hh, age, order) -> total
errs = []
in_table, cols, hh = False, None, None
for raw in open(src, encoding="utf-8"):
    ln = norm(raw).strip()
    if "第4表" in ln and "出生順位" in ln:
        in_table, cols = True, None
        continue
    if not in_table:
        continue
    if re.match(r"^第4子", ln) or ("第4子" in ln and "第5子以上" in ln):
        cols = ORDERS_B
        continue
    if ln.startswith("総数") and "第1子" in ln:
        cols = ORDERS_A
        continue
    m = re.match(r"^\(\s*(.+?)\s*\)$", ln)
    if m:
        name = m.group(1).replace(" ", "")
        name = name.replace("I", "Ⅰ").replace("II", "Ⅱ") if False else name
        key = norm(name)
        # NFKC turns Ⅰ/Ⅱ into I/II
        hh = HH_N.get(key)
        if hh is None:
            errs.append(f"unknown household label {name}")
        continue
    if cols is None or hh is None:
        continue
    tok = ln.split()
    if not tok:
        continue
    label = tok[0]
    age = AGE_N.get(label)
    if age is None:
        if ln.startswith("S-") or label.startswith("令和") or label.startswith("平成") or label == "母の年齢":
            continue
        continue
    vals = [num(t) for t in tok[1:]]
    if any(v is None for v in vals) or len(vals) != 3 * len(cols):
        errs.append(f"{hh}/{age}: {len(vals)} values, cols={len(cols)}")
        continue
    for i, o in enumerate(cols):
        t, mm, f = vals[3 * i:3 * i + 3]
        if t != mm + f:
            errs.append(f"{hh}/{age}/{o}: {t}!={mm}+{f}")
        key = (hh, age, o)
        if key in data and data[key] != t:
            errs.append(f"duplicate mismatch {key}")
        data[key] = t

ORD_ALL = ["第1子", "第2子", "第3子", "第4子", "第5子以上", "不詳"]
for h in HH:
    for a in AGES:
        if (h, a, "総数") not in data:
            errs.append(f"missing {h}/{a}")
            continue
        s = sum(data.get((h, a, o), 0) for o in ORD_ALL)
        if s != data[(h, a, "総数")]:
            errs.append(f"order sum {h}/{a}: {s} != {data[(h, a, '総数')]}")
    for o in ["総数"] + ORD_ALL:
        s = sum(data.get((h, a, o), 0) for a in AGES[1:])
        if (h, "総数", o) in data and s != data[(h, "総数", o)]:
            errs.append(f"age sum {h}/{o}: {s} != {data[(h, '総数', o)]}")
for a in AGES:
    for o in ["総数"] + ORD_ALL:
        s = sum(data.get((h, a, o), 0) for h in HH[1:])
        if ("総数", a, o) in data and s != data[("総数", a, o)]:
            errs.append(f"household sum {a}/{o}: {s} != {data[('総数', a, o)]}")

if errs:
    print(f"{year} QA FAILED ({len(errs)})")
    for e in errs[:25]:
        print("  ", e)
    sys.exit(1)

with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["year", "household_type", "age_group", "birth_order", "births", "value_status", "extraction"])
    for (h, a, o), v in sorted(data.items(), key=lambda kv: (HH.index(kv[0][0]), AGES.index(kv[0][1]), (["総数"] + ORD_ALL).index(kv[0][2]))):
        w.writerow([year, h, a, o, v, "observed", extraction])
print(f"{year} QA passed: total={data[('総数','総数','総数')]} first={data[('総数','総数','第1子')]} cells={len(data)}")
