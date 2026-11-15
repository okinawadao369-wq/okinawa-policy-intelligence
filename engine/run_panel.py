"""W4: 市町村パネルによる関連分析（関連の推定であり、因果効果ではない: inference_class='associational'）

モデル1（年次パネル, 2015-2024, 41市町村）
  出生数_it ~ Poisson( exp( log(女性15-49年央_it) + α_i + γ_t + β·log(納税義務者1人当たり課税対象所得_i,t) ) )
  - 課税対象所得の「年度t」は前年（t-1暦年）の所得 → 出生年tに対し自然に1年ラグ
  - 年固定効果 γ_t が県共通の物価・賃金・制度ショック（G02）を吸収するため、名目所得のままでよい（実質化は γ_t に吸収）
  - 標準誤差: 市町村クラスターのペア・ブートストラップ（999回）
モデル2: モデル1 + log(婚姻件数/女性15-49) … 婚姻は出生の経路（媒介）なので、所得係数の変化は「婚姻経由の関連」を示唆するにとどまる

横断（5年プール 2020-2024 の合計特殊出生率 × 国勢調査2020・住宅土地統計2023）
  女性労働力率、民営借家比率、未婚者割合(15歳以上) とのスピアマン相関 + ブートストラップ区間
"""
import csv, json, pathlib, hashlib, subprocess
from collections import defaultdict
import numpy as np, pandas as pd, statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGES = ["15-19歳", "20-24歳", "25-29歳", "30-34歳", "35-39歳", "40-44歳", "45-49歳"]
munis = {r["muni_code5"]: r for r in csv.DictReader(open(ROOT / "data/municipalities.csv", encoding="utf-8"))}

births = defaultdict(float)
for r in csv.DictReader(open(ROOT / "data/births_by_mother_age.csv", encoding="utf-8")):
    if r["muni_code5"] in munis and r["age_group"] == "総数": births[(r["muni_code5"], int(r["year"]))] = float(r["births"])
J = defaultdict(float)
for r in csv.DictReader(open(ROOT / "data/juki_female_japanese.csv", encoding="utf-8")):
    J[(r["muni_code5"], int(r["ref_date"][:4]))] += float(r["female_japanese"])
mar = {}
for r in csv.DictReader(open(ROOT / "data/marriages.csv", encoding="utf-8")):
    if r["muni_code5"] in munis: mar[(r["muni_code5"], int(r["year"]))] = float(r["marriages_total"])
S = defaultdict(dict)
for r in csv.DictReader(open(ROOT / "data/estat/ssds_okinawa.csv", encoding="utf-8")):
    try: S[r["item_code"]][(r["area"], int(r["time"][:4]))] = float(r["value"])
    except ValueError: pass  # e-Statの「-」「…」等は欠損として扱う（0にしない）

rows = []
for c in munis:
    for y in range(2015, 2025):
        w = (J[(c, y)] + J[(c, y + 1)]) / 2
        inc, tax = S["C120110"].get((c, y)), S["C120120"].get((c, y))
        rows.append(dict(code=c, year=y, births=births[(c, y)], women=w, marriages=mar.get((c, y)),
                         inc_per_taxpayer=(inc / tax) if inc and tax else np.nan))
df = pd.DataFrame(rows)
df["log_inc"] = np.log(df["inc_per_taxpayer"])
df["log_mar_rate"] = np.log((df["marriages"] + 0.5) / df["women"])  # 0件の年に備え+0.5
df = df.dropna(subset=["log_inc"]).reset_index(drop=True)

def fit(d, xs):
    X = pd.get_dummies(d[["code", "year"]].astype(str), drop_first=True, dtype=float)
    X = pd.concat([d[xs], X], axis=1); X = sm.add_constant(X)
    m = sm.GLM(d["births"], X, family=sm.families.Poisson(), offset=np.log(d["women"])).fit()
    return m.params[xs].values, m

def cluster_boot(xs, reps=999, seed=20261115):
    rng = np.random.default_rng(seed); codes = df["code"].unique(); est = []
    for _ in range(reps):
        pick = rng.choice(codes, len(codes), replace=True)
        parts = [df[df.code == c].assign(code=f"{c}_{i}") for i, c in enumerate(pick)]
        try: est.append(fit(pd.concat(parts, ignore_index=True), xs)[0])
        except Exception: pass
    est = np.array(est)
    return np.percentile(est, 2.5, axis=0), np.percentile(est, 97.5, axis=0), len(est)

results = []
for name, xs in [("model1_income", ["log_inc"]), ("model2_income_marriage", ["log_inc", "log_mar_rate"])]:
    b, m = fit(df, xs); lo, hi, n_ok = cluster_boot(xs)
    for k, x in enumerate(xs):
        results.append(dict(model=name, term=x, estimate=round(b[k], 4), ci_low=round(lo[k], 4), ci_high=round(hi[k], 4),
                            irr_10pct=round(float(np.exp(b[k] * np.log(1.1))), 4),
                            n_obs=len(df), n_munis=df.code.nunique(), boot_ok=n_ok, inference_class="associational",
                            note="市町村・年固定効果つきポアソン。区間は市町村クラスター・ブートストラップ95%"))

# 横断: 2020-24プールTFR vs 2020国勢調査・2023住宅
AG = defaultdict(float); WA = defaultdict(float)
for r in csv.DictReader(open(ROOT / "data/births_by_mother_age.csv", encoding="utf-8")):
    y = int(r["year"])
    if r["muni_code5"] in munis and 2020 <= y <= 2024 and r["age_group"] not in ("総数", "不詳"):
        a = {"14歳以下": "15-19歳", "50歳以上": "45-49歳"}.get(r["age_group"], r["age_group"]); AG[(r["muni_code5"], a)] += float(r["births"])
for r in csv.DictReader(open(ROOT / "data/juki_female_japanese.csv", encoding="utf-8")):
    y = int(r["ref_date"][:4]); c = r["muni_code5"]
    if 2020 <= y <= 2025: WA[(c, r["age_group"])] += float(r["female_japanese"]) * (0.5 if y in (2020, 2025) else 1.0)
cross = []
for c in munis:
    tfr = sum(5 * AG[(c, a)] / WA[(c, a)] for a in AGES if WA[(c, a)] > 0)
    lf, nlf = S["F110102"].get((c, 2020)), S["F110802"].get((c, 2020))
    own, rent, priv = S["H1310"].get((c, 2023)), S["H1320"].get((c, 2023)), S["H1322"].get((c, 2023))
    cross.append(dict(code=c, name=munis[c]["name_ja"], tfr_2020_24=round(tfr, 3),
                      female_lfpr_2020=round(lf / (lf + nlf), 4) if lf and nlf else None,
                      private_rental_share_2023=round(priv / (own + rent), 4) if own and rent and priv else None,
                      unmarried_share_15p_2020=S["A161001"].get((c, 2020)),
                      births_2020_24=sum(births[(c, y)] for y in range(2020, 2025))))
cd = pd.DataFrame(cross)
rng = np.random.default_rng(20261115)
for v in ["female_lfpr_2020", "private_rental_share_2023", "unmarried_share_15p_2020"]:
    d = cd.dropna(subset=[v]); rho = d["tfr_2020_24"].corr(d[v], method="spearman")
    bs = [d.iloc[rng.integers(0, len(d), len(d))].pipe(lambda z: z["tfr_2020_24"].corr(z[v], method="spearman")) for _ in range(2000)]
    results.append(dict(model="cross_section_2020_24", term=v, estimate=round(rho, 3), ci_low=round(np.nanpercentile(bs, 2.5), 3),
                        ci_high=round(np.nanpercentile(bs, 97.5), 3), irr_10pct=None, n_obs=len(d), n_munis=len(d), boot_ok=2000,
                        inference_class="descriptive", note="スピアマン順位相関（41市町村、小規模町村も同じ重み）"))

out = ROOT / "results"; out.mkdir(exist_ok=True)
pd.DataFrame(results).to_csv(out / "panel_associations.csv", index=False)
cd.to_csv(out / "cross_section_2020_24.csv", index=False)
inputs = b"".join(open(ROOT / p, "rb").read() for p in ["data/births_by_mother_age.csv", "data/juki_female_japanese.csv", "data/marriages.csv", "data/estat/ssds_okinawa.csv"])
try: sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
except Exception: sha = "unknown"
json.dump(dict(run_id="w4-panel", method="fe_poisson+cluster_bootstrap; spearman", git_sha_base=sha, input_hash=hashlib.sha256(inputs).hexdigest(),
               params=dict(cluster_boot=999, seed=20261115), inference_class="associational"), open(out / "model_run_w4.json", "w"), ensure_ascii=False, indent=2)
print(pd.DataFrame(results)[["model", "term", "estimate", "ci_low", "ci_high", "irr_10pct", "n_obs", "boot_ok"]].to_string())
