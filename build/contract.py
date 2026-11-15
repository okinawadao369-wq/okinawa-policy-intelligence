#!/usr/bin/env python3
"""Build Contract: site/ の成果物が満たすべき条件を検査する（失敗で終了コード1）。"""
import json, pathlib, re, sys
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / "site/index.html").read_text(encoding="utf-8")
d = json.loads((root / "site/data.json").read_text(encoding="utf-8"))
errs = []
if "/*__DATA__*/null" in html: errs.append("データが埋め込まれていない")
if re.search(r'<(script|link)[^>]+(src|href)="https?://', html): errs.append("外部スクリプト/スタイルの読み込みがある（オフライン要件違反）")
if re.search(r"\bfetch\(|XMLHttpRequest", html): errs.append("外部通信のコードがある")
lv = [u["level"] for u in d["units"]]
if lv.count("municipality") != 41 or lv.count("prefecture") != 1 or lv.count("health_center") != 6: errs.append(f"地域単位の数が不正 {lv.count('municipality')}")
for uid, s in d["series"].items():
    if [r["year"] for r in s] != list(range(2015, 2025)): errs.append(f"{uid}: 年が不正")
p = d["series"]["47000"]
if sum(sum(d["series"][u["id"]][i]["births"] for u in d["units"] if u["level"] == "municipality") != p[i]["births"] for i in range(10)): errs.append("市町村合計≠県")
if {r["unit_id"] for r in d["decomposition"]} != {u["id"] for u in d["units"]}: errs.append("要因分解の地域が画面の地域と不一致")
bo = d.get("birth_order", {})
if [int(r["year"]) for r in bo.get("series", [])] != list(range(2015, 2025)): errs.append("出生順位: 年が不正")
for r, s in zip(bo.get("series", []), p):
    if sum(int(r[k]) for k in ("births_第1子", "births_第2子", "births_第3子以上")) != s["births"]: errs.append(f"出生順位: {r['year']} 順位計≠県の出生数")
if any(r.get("value_status") != "estimated" for r in bo.get("projection", [])): errs.append("出生順位: 試算に estimated 表示がない")
for o in d["official_tfr_pref"]:
    if not o.get("url"): errs.append("公表値に出典URLがない")
print("\n".join(errs) or "Build contract passed"); sys.exit(1 if errs else 0)
