"""W9: 出生順位別の分析（沖縄県全体、2015–2024）。results/ に書き出す。

データ:
  出生: data/births_by_order.csv（県年報 出生第4表、日本における日本人の出生、observed）
  分母: 住基 日本人女性（41市町村計）の年央近似 =(当年1/1+翌年1/1)/2（D-001）
区分: 第1子 / 第2子 / 第3子以上（出生順位は「同じ母が生んだ出生子の順位」。不詳は全年0）
出力:
  results/birth_order_series.csv       年×順位の出生数・構成比・順位別TFR・第1子の母の平均年齢 等
  results/birth_order_decomp.csv       2015→2024 の順位別「人口要因／出生率要因」分解（95%CI付き）
  results/first_birth_projection.csv   第1子出生数の2025–2030年の試算（estimated。シナリオ幅）
  results/first_birth_backtest.csv     同じ試算方法の過去検証（2015–19の情報だけで2020–24を当てる）
  results/model_run_w9.json
いずれも記述・試算であり因果効果の推定ではない（inference_class = descriptive / projection）。
"""
import csv, json, pathlib, hashlib, subprocess, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from decomposition import decompose_counts, bootstrap_ci

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGES = ["15-19歳", "20-24歳", "25-29歳", "30-34歳", "35-39歳", "40-44歳", "45-49歳"]
MID = np.array([17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5])
FOLD = {"14歳以下": "15-19歳", "50歳以上": "45-49歳"}
ORD = {"第1子": "第1子", "第2子": "第2子", "第3子": "第3子以上", "第4子": "第3子以上", "第5子以上": "第3子以上"}
ORDERS = ["第1子", "第2子", "第3子以上"]
YEARS = list(range(2015, 2025))
HH_GROUPS = {"常用勤労者世帯（Ⅰ+Ⅱ）": ["常用勤労者世帯Ⅰ", "常用勤労者世帯Ⅱ"], "自営業者・農家": ["自営業者世帯", "農家世帯"],
             "その他・無職・不詳": ["その他の世帯", "無職の世帯", "不詳"]}

B = defaultdict(float)       # (year, order, age)
HHB = defaultdict(float)     # (year, order, household_type)
for r in csv.DictReader(open(ROOT / "data/births_by_order.csv", encoding="utf-8")):
    if r["birth_order"] not in ORD:
        continue
    o, y = ORD[r["birth_order"]], int(r["year"])
    if r["household_type"] == "総数" and r["age_group"] not in ("総数", "不詳"):
        B[(y, o, FOLD.get(r["age_group"], r["age_group"]))] += float(r["births"])
    if r["household_type"] != "総数" and r["age_group"] == "総数":
        HHB[(y, o, r["household_type"])] += float(r["births"])

munis = [r["muni_code5"] for r in csv.DictReader(open(ROOT / "data/municipalities.csv", encoding="utf-8"))]
J = defaultdict(float)
for r in csv.DictReader(open(ROOT / "data/juki_female_japanese.csv", encoding="utf-8")):
    if r["muni_code5"] in munis:
        J[(int(r["ref_date"][:4]), r["age_group"])] += float(r["female_japanese"])
JY = sorted({k[0] for k in J})

def jan1(y):
    return np.array([J[(y, a)] for a in AGES])
def W(y):
    return (jan1(y) + jan1(y + 1)) / 2
def Bv(y, o):
    return np.array([B[(y, o, a)] for a in AGES])

out = ROOT / "results"
out.mkdir(exist_ok=True)

# 1) 系列
rows = []
for y in YEARS:
    tot = sum(Bv(y, o).sum() for o in ORDERS)
    w = W(y)
    row = {"year": y, "births_total": int(tot), "women15_49_mid": round(w.sum())}
    for o in ORDERS:
        b = Bv(y, o)
        row[f"births_{o}"] = int(b.sum())
        row[f"share_{o}"] = round(b.sum() / tot, 4)
        row[f"tfr_{o}"] = round(float(5 * (b / w).sum()), 4)   # 順位別の期間合計出生率
    b1 = Bv(y, "第1子")
    row["mean_age_first_birth_approx"] = round(float((b1 * MID).sum() / b1.sum()), 2)
    row["share_first_births_mother35plus"] = round(float(b1[4:].sum() / b1.sum()), 4)
    row["share_first_births_mother_u25"] = round(float(b1[:2].sum() / b1.sum()), 4)
    hh_tot = sum(HHB[(y, "第1子", h)] for g in HH_GROUPS.values() for h in g)
    for g, hs in HH_GROUPS.items():
        row[f"first_birth_hh_share_{g}"] = round(sum(HHB[(y, "第1子", h)] for h in hs) / hh_tot, 4)
    rows.append(row)
with open(out / "birth_order_series.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
    wr.writeheader(); wr.writerows(rows)

# 2) 順位別の要因分解 2015 → 2024（ポアソン・ブートストラップ 95%CI）
dec = []
W1, W2 = W(2015), W(2024)
for o in ORDERS:
    d = decompose_counts(Bv(2015, o), W1, Bv(2024, o), W2)
    ci = bootstrap_ci(Bv(2015, o), W1, Bv(2024, o), W2)
    dec.append({"birth_order": o, "births_2015": int(Bv(2015, o).sum()), "births_2024": int(Bv(2024, o).sum()),
                "delta": round(d["total"]), "population_effect": round(d["population_effect"]),
                "rate_effect": round(d["rate_effect"]),
                "rate_effect_ci95": f"{round(ci['rate_effect'][0])}..{round(ci['rate_effect'][1])}",
                "population_effect_ci95": f"{round(ci['population_effect'][0])}..{round(ci['population_effect'][1])}"})
with open(out / "birth_order_decomp.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(dec[0]))
    wr.writeheader(); wr.writerows(dec)

# 3) 第1子出生数の試算（コーホート移動による将来の女性人口 × 年齢別第1子出生率のシナリオ）
def jan1_future(y):
    """住基1/1が無い年は5年前の1つ下の年齢階級から移す（転出入・死亡は無視）。15-19歳は最新年の値で固定。"""
    if y in JY:
        return jan1(y)
    base = jan1(y - 5)
    last = max(JY)
    return np.array([jan1(last)[0]] + list(base[:-1]))
def W_future(y):
    return (jan1_future(y) + jan1_future(y + 1)) / 2

def rates(y):
    return Bv(y, "第1子") / W(y)
def trend_rates(y0, y1, target):
    """y0..y1 の各年齢の第1子出生率を対数線形で延長"""
    ys = np.arange(y0, y1 + 1)
    R = np.array([rates(y) for y in ys])
    out_r = []
    for i in range(len(AGES)):
        r = np.clip(R[:, i], 1e-9, None)
        k, c = np.polyfit(ys, np.log(r), 1)
        out_r.append(np.exp(c + k * target))
    return np.array(out_r)

proj = []
for y in range(2025, 2031):
    w = W_future(y)
    sc = {"A_2024率で固定": rates(2024),
          "B_2022-24平均率": (rates(2022) + rates(2023) + rates(2024)) / 3,
          "C_2015-24傾向で延長": trend_rates(2015, 2024, y)}
    rec = {"year": y, "women15_49_mid_est": round(w.sum()), "women25_39_mid_est": round(w[2:5].sum())}
    for k, r in sc.items():
        rec[f"first_births_{k}"] = round(float((w * r).sum()))
    rec["value_status"] = "estimated"
    proj.append(rec)
with open(out / "first_birth_projection.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(proj[0]))
    wr.writeheader(); wr.writerows(proj)

# 4) 過去検証: 2015–2019 の情報だけで 2020–2024 の第1子数を当てる（女性人口は実績を使用）
bt = []
for y in range(2020, 2025):
    act = Bv(y, "第1子").sum()
    a = float((W(y) * rates(2019)).sum())
    c = float((W(y) * trend_rates(2015, 2019, y)).sum())
    bt.append({"year": y, "actual": int(act), "A_fixed2019": round(a), "A_err_pct": round(100 * (a - act) / act, 1),
               "C_trend2015_19": round(c), "C_err_pct": round(100 * (c - act) / act, 1)})
with open(out / "first_birth_backtest.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(bt[0]))
    wr.writeheader(); wr.writerows(bt)

sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
inputs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]
          for p in ["data/births_by_order.csv", "data/juki_female_japanese.csv"]}
json.dump({"model_run": "w9_birth_order", "git_sha": sha, "inputs_sha256_16": inputs,
           "inference_class": ["descriptive", "projection"],
           "notes": ["出生順位は県全体のみ（市町村別は非公表・D-007）",
                     "対象は日本における日本人の出生。在沖米軍・軍属（SOFA）家族の出生は含まない",
                     "将来女性人口はコーホート移動のみ（転出入・死亡を無視）。15-19歳は2026年値で固定",
                     "試算はシナリオであり予測の確約ではない"]},
          open(out / "model_run_w9.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("series"); [print(r) for r in rows]
print("decomp"); [print(r) for r in dec]
print("projection"); [print(r) for r in proj]
print("backtest"); [print(r) for r in bt]
