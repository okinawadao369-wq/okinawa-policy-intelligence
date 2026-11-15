"""W3: 出生数変化の対称要因分解を実データで実行し、results/ に書き出す。

- 単年比較: 2015 → 2024（県・保健所圏域・市町村）
- 5年プール比較: 2015-2019 → 2020-2024（小規模市町村の安定化。G08）
- 分母: 住基 日本人女性の年央近似 = (当年1/1 + 翌年1/1)/2（D-001）
- 14歳以下は15-19歳、50歳以上は45-49歳に含める（年齢別出生率の慣行）
- 不確実性: 出生数のポアソン・ブートストラップ（2,000回、乱数種固定）
- inference_class = descriptive（因果効果の推定ではない）
"""
import csv, json, pathlib, hashlib, subprocess, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from decomposition import decompose_counts, bootstrap_ci

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGES = ["15-19歳", "20-24歳", "25-29歳", "30-34歳", "35-39歳", "40-44歳", "45-49歳"]
FOLD = {"14歳以下": "15-19歳", "50歳以上": "45-49歳"}

munis = {r["muni_code5"]: r for r in csv.DictReader(open(ROOT / "data/municipalities.csv", encoding="utf-8"))}
B = defaultdict(float)
for r in csv.DictReader(open(ROOT / "data/births_by_mother_age.csv", encoding="utf-8")):
    if r["muni_code5"] in munis and r["age_group"] not in ("総数", "不詳"):
        B[(r["muni_code5"], int(r["year"]), FOLD.get(r["age_group"], r["age_group"]))] += float(r["births"])
J = {}
for r in csv.DictReader(open(ROOT / "data/juki_female_japanese.csv", encoding="utf-8")):
    J[(r["muni_code5"], int(r["ref_date"][:4]), r["age_group"])] = float(r["female_japanese"])

def W(codes, y):  # 年央人口の近似（年齢別ベクトル）
    return np.array([sum((J[(c, y, a)] + J[(c, y + 1, a)]) / 2 for c in codes) for a in AGES])
def Bv(codes, y):
    return np.array([sum(B[(c, y, a)] for c in codes) for a in AGES])
def pooled(codes, years):
    return sum(Bv(codes, y) for y in years), sum(W(codes, y) for y in years)

units = [("47000", "沖縄県", "prefecture", list(munis))]
hc = defaultdict(list)
for c, m in munis.items(): hc[m["health_center"]].append(c)
units += [(f"HC:{k}", k, "health_center", v) for k, v in sorted(hc.items())]
units += [(c, m["name_ja"], "municipality", [c]) for c, m in sorted(munis.items())]

rows = []
for uid, name, level, codes in units:
    for label, y1, y2 in [("single_2015_2024", [2015], [2024]), ("pooled_2015-19_2020-24", range(2015, 2020), range(2020, 2025))]:
        b1, w1 = pooled(codes, y1); b2, w2 = pooled(codes, y2)
        if np.any(w1 <= 0) or np.any(w2 <= 0):
            rows.append(dict(unit_id=uid, name=name, level=level, comparison=label, births_1=b1.sum(), births_2=b2.sum(),
                             change=None, population_effect=None, rate_effect=None, pop_ci_low=None, pop_ci_high=None,
                             rate_ci_low=None, rate_ci_high=None, tfr_1=None, tfr_2=None, status="missing_suppressed",
                             note="分母に0の年齢階級があり年齢別出生率が未定義")); continue
        d = decompose_counts(b1, w1, b2, w2)
        ci = bootstrap_ci(b1, w1, b2, w2, n=2000, seed=20261115)
        k1, k2 = len(list(y1)), len(list(y2))
        rows.append(dict(unit_id=uid, name=name, level=level, comparison=label,
                         births_1=round(b1.sum() / k1, 1), births_2=round(b2.sum() / k2, 1),  # 年平均
                         change=round(d["total"] / k1, 1) if k1 == k2 else None,
                         population_effect=round(d["population_effect"] / k1, 1), rate_effect=round(d["rate_effect"] / k1, 1),
                         pop_ci_low=round(ci["population_effect"][0] / k1, 1), pop_ci_high=round(ci["population_effect"][1] / k1, 1),
                         rate_ci_low=round(ci["rate_effect"][0] / k1, 1), rate_ci_high=round(ci["rate_effect"][1] / k1, 1),
                         tfr_1=round(float((5 * b1 / w1).sum()), 3), tfr_2=round(float((5 * b2 / w2).sum()), 3),
                         status="estimated", note="年平均値（プール比較は5年平均）。区間はポアソン・ブートストラップ95%"))

out = ROOT / "results"; out.mkdir(exist_ok=True)
with open(out / "decomposition_2015_2024.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

inputs = b"".join(open(ROOT / p, "rb").read() for p in ["data/births_by_mother_age.csv", "data/juki_female_japanese.csv", "data/municipalities.csv"])
try: sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
except Exception: sha = "unknown"
json.dump(dict(run_id="w3-decomp-2015-2024", method="symmetric_decomposition", git_sha_base=sha,
               input_hash=hashlib.sha256(inputs).hexdigest(), params=dict(bootstrap=2000, seed=20261115, denominator="juki_japanese_female_midyear"),
               inference_class="descriptive"), open(out / "model_run_w3.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(rows)} rows written")
