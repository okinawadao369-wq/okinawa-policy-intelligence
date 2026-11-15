#!/usr/bin/env python3
"""e-Stat API（社会・人口統計体系 市区町村データ 基礎データ 廃置分合処理済）から沖縄41市町村の指標を取得。
appId は環境変数 ESTAT_APP_ID（GitHub Secrets）からのみ読み、出力・ログに残さない。
出力: data/estat/ssds_meta_<id>.json（項目一覧）, data/estat/ssds_okinawa.csv（選択項目のロング形式）"""
import os, json, csv, urllib.request, urllib.parse, pathlib, sys, time
KEY = os.environ.get("ESTAT_APP_ID", "").strip()
if not KEY: sys.exit("ESTAT_APP_ID is not set")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/estat"; OUT.mkdir(parents=True, exist_ok=True)
TABLES = {"0000020201": "A 人口・世帯", "0000020203": "C 経済基盤", "0000020206": "F 労働", "0000020208": "H 居住"}
KEYWORDS = ["課税対象所得", "納税義務者", "未婚", "有配偶", "配偶", "家賃", "借家", "持ち家", "完全失業", "労働力", "就業者", "共働き", "出生", "婚姻"]
AREAS = [r["muni_code5"] for r in csv.DictReader(open(ROOT / "data/municipalities.csv", encoding="utf-8"))]
BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/"
def call(fn, **p):
    p["appId"] = KEY
    url = BASE + fn + "?" + urllib.parse.urlencode(p)
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"{fn} retry {i+1}: {type(e).__name__}"); time.sleep(5)
    sys.exit(f"{fn} failed")
rows = []
for tid, tname in TABLES.items():
    meta = call("getMetaInfo", statsDataId=tid)
    res = meta["GET_META_INFO"]["RESULT"]
    if res["STATUS"] != 0: sys.exit(f"meta {tid}: {res['ERROR_MSG']}")
    objs = meta["GET_META_INFO"]["METADATA_INF"]["CLASS_INF"]["CLASS_OBJ"]
    cat = next(o for o in objs if o["@id"] == "cat01")
    items = cat["CLASS"] if isinstance(cat["CLASS"], list) else [cat["CLASS"]]
    json.dump([{"code": c["@code"], "name": c["@name"], "unit": c.get("@unit")} for c in items],
              open(OUT / f"ssds_meta_{tid}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pick = [c["@code"] for c in items if any(k in c["@name"] for k in KEYWORDS)]
    print(tid, tname, "items", len(items), "picked", len(pick))
    for i in range(0, len(pick), 50):
        d = call("getStatsData", statsDataId=tid, cdCat01=",".join(pick[i:i+50]), cdArea=",".join(AREAS), limit=100000)
        r = d["GET_STATS_DATA"]["RESULT"]
        if r["STATUS"] not in (0, 1): sys.exit(f"data {tid}: {r['ERROR_MSG']}")
        if r["STATUS"] == 1: continue
        sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
        names = {c["@code"]: c["@name"] for o in sd["CLASS_INF"]["CLASS_OBJ"] if o["@id"] == "cat01"
                 for c in (o["CLASS"] if isinstance(o["CLASS"], list) else [o["CLASS"]])}
        vals = sd["DATA_INF"]["VALUE"]; vals = vals if isinstance(vals, list) else [vals]
        for v in vals:
            rows.append({"table_id": tid, "item_code": v["@cat01"], "item_name": names.get(v["@cat01"], ""), "area": v["@area"],
                         "time": v["@time"], "unit": v.get("@unit", ""), "value": v["$"]})
with open(OUT / "ssds_okinawa.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["table_id", "item_code", "item_name", "area", "time", "unit", "value"]); w.writeheader(); w.writerows(rows)
print("rows", len(rows))
