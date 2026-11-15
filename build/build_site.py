#!/usr/bin/env python3
"""ダッシュボードのビルド: data/ と results/ から site/index.html（データ埋め込みの単一HTML）と site/data.json を生成。
外部CDN・外部通信なし（オフラインで動く）。Build Contract: build/contract.py で検証する。"""
import csv, json, pathlib, subprocess
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGES = ["15-19歳", "20-24歳", "25-29歳", "30-34歳", "35-39歳", "40-44歳", "45-49歳"]
FOLD = {"14歳以下": "15-19歳", "50歳以上": "45-49歳"}
YEARS = list(range(2015, 2025))
rd = lambda p: list(csv.DictReader(open(ROOT / p, encoding="utf-8")))

munis = rd("data/municipalities.csv")
units = [{"id": "47000", "name": "沖縄県", "level": "prefecture", "codes": [m["muni_code5"] for m in munis]}]
hc = defaultdict(list)
for m in munis: hc[m["health_center"]].append(m["muni_code5"])
units += [{"id": f"HC:{k}", "name": k, "level": "health_center", "codes": v} for k, v in sorted(hc.items())]
units += [{"id": m["muni_code5"], "name": m["name_ja"], "level": "municipality", "codes": [m["muni_code5"]],
           "health_center": m["health_center"], "lg_code6": m["lg_code6"]} for m in munis]

B = defaultdict(float); BT = defaultdict(float)
for r in rd("data/births_by_mother_age.csv"):
    if r["muni_code5"] == "47000": continue
    if r["age_group"] == "総数": BT[(r["muni_code5"], int(r["year"]))] = float(r["births"])
    elif r["age_group"] != "不詳": B[(r["muni_code5"], int(r["year"]), FOLD.get(r["age_group"], r["age_group"]))] += float(r["births"])
M = {(r["muni_code5"], int(r["year"])): (float(r["marriages_total"]), float(r["marriages_both_first"])) for r in rd("data/marriages.csv") if r["muni_code5"] != "47000"}
J = {(r["muni_code5"], int(r["ref_date"][:4]), r["age_group"]): float(r["female_japanese"]) for r in rd("data/juki_female_japanese.csv")}
S = defaultdict(dict)
for r in rd("data/estat/ssds_okinawa.csv"):
    try: S[r["item_code"]][(r["area"], int(r["time"][:4]))] = float(r["value"])
    except ValueError: pass

def series(codes):
    out = []
    for y in YEARS:
        w = {a: sum((J[(c, y, a)] + J[(c, y + 1, a)]) / 2 for c in codes) for a in AGES}
        b = {a: sum(B[(c, y, a)] for c in codes) for a in AGES}
        tfr = sum(5 * b[a] / w[a] for a in AGES) if all(w[a] > 0 for a in AGES) else None
        inc = [S["C120110"].get((c, y)) for c in codes]; tax = [S["C120120"].get((c, y)) for c in codes]
        ipt = (sum(inc) / sum(tax) * 1000) if all(inc) and all(tax) else None  # 千円→円
        out.append({"year": y, "births": sum(BT[(c, y)] for c in codes), "marriages": sum(M[(c, y)][0] for c in codes),
                    "marriages_first": sum(M[(c, y)][1] for c in codes), "women15_49": round(sum(w.values())),
                    "tfr_est": round(tfr, 3) if tfr is not None else None,
                    "income_per_taxpayer": round(ipt) if ipt else None,
                    "births_by_age": {a: b[a] for a in AGES}})
    return out

data = {
    "built_from": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown",
    "units": [{k: v for k, v in u.items() if k != "codes"} | {"n_munis": len(u["codes"])} for u in units],
    "series": {u["id"]: series(u["codes"]) for u in units},
    "decomposition": rd("results/decomposition_2015_2024.csv"),
    "associations": rd("results/panel_associations.csv"),
    "sources": rd("data/source_catalog.csv"),
    "official_tfr_pref": [
        {"year": 2020, "tfr": 1.83, "source": "沖縄県 令和2年人口動態統計（確定数）の概況", "url": "https://www.pref.okinawa.jp/_res/projects/default_project/_page_/001/016/429/r2jinkoudoutai.pdf"},
        {"year": 2023, "tfr": 1.60, "source": "琉球新報（県人口動態統計 確定数）", "url": "https://ryukyushimpo.jp/tag/出生率"},
        {"year": 2024, "tfr": 1.54, "source": "琉球新報（厚労省 人口動態統計 概数）", "url": "https://ryukyushimpo.jp/tag/出生率"}],
    "issues": [
        {"id": "G01", "type": "欠損", "text": "出生順位×市町村は県年報に無い（県計のみ）。二次利用申請は保留（D-002）"},
        {"id": "G02", "type": "欠損", "text": "賃金・物価は県単位のみ。年固定効果で吸収し、市町村差は課税対象所得で代替"},
        {"id": "G03", "type": "欠損", "text": "2025年の出生確定数は未掲載（未取得）"},
        {"id": "G04", "type": "欠損", "text": "住宅・土地統計は19市町村、家賃は11市のみ表章"},
        {"id": "G05", "type": "定義差", "text": "分母は住基日本人女性（1/1）。公表TFR（人口推計10/1）より約0.05低い"},
        {"id": "G06", "type": "定義差", "text": "SOFA世帯は住民登録・県推計の対象外（規模は未立証）"},
        {"id": "G08", "type": "少数", "text": "出生50人未満の町村は単年の率が不安定。5年プール比較を主に使う"},
        {"id": "G14", "type": "照合", "text": "e-Stat値と県年報が369セル中3セルで1件差（原文確認済み）"}],
}
site = ROOT / "site"; site.mkdir(exist_ok=True)
(site / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
tpl = (ROOT / "build/template.html").read_text(encoding="utf-8")
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
(site / "index.html").write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")
print("units", len(data["units"]), "bytes", len((site / "index.html").read_bytes()))
