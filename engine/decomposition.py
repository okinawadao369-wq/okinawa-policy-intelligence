"""KOYA Okinawa Policy Intelligence — 出生数変化の対称要因分解（Phase 2-1〜2-3, 2-7）

定義:  B_t = Σ_a W_{a,t} · f_{a,t}
  W_{a,t}: 年齢階級 a の女性人口（分母）  f_{a,t} = B_{a,t} / W_{a,t}: 年齢別出生率
対称（Das Gupta 2要因・中点）分解:
  ΔB = Σ_a (W2-W1)(f1+f2)/2   ← 人口要因
     + Σ_a (f2-f1)(W1+W2)/2   ← 出生率要因
  2項の和は ΔB と厳密に一致する（残差なし）。
出生順位 k 別: B_{k,t} = Σ_a W_{a,t} f_{a,k,t} に同じ分解を適用し、Σ_k は全体の分解と一致する。

不確実性: 出生数をポアソン分布で再標本化するパラメトリック・ブートストラップ（女性人口は固定）。
  小規模村（年数件）では区間が広く出ることを正しく示すためのもの。
  分母定義の違い（住基日本人 vs 推計人口）は sensitivity() で別途比較する。

この関数群は記述的分解であり、因果効果を推定するものではない（inference_class='descriptive'）。
"""
from __future__ import annotations
import numpy as np

def asfr(births, women):
    births, women = np.asarray(births, float), np.asarray(women, float)
    if np.any(women <= 0):
        raise ValueError("女性人口が0以下の年齢階級がある（分母欠損は推計しない）")
    return births / women

def decompose(W1, f1, W2, f2):
    """戻り値: dict(total, population_effect, rate_effect, by_age_pop, by_age_rate)"""
    W1, f1, W2, f2 = (np.asarray(x, float) for x in (W1, f1, W2, f2))
    pop = (W2 - W1) * (f1 + f2) / 2
    rate = (f2 - f1) * (W1 + W2) / 2
    total = float((W2 * f2).sum() - (W1 * f1).sum())
    out = dict(total=total, population_effect=float(pop.sum()), rate_effect=float(rate.sum()),
               by_age_pop=pop, by_age_rate=rate)
    assert abs(out["population_effect"] + out["rate_effect"] - total) < 1e-6 * max(1, abs(total))
    return out

def decompose_counts(B1, W1, B2, W2):
    return decompose(W1, asfr(B1, W1), W2, asfr(B2, W2))

def decompose_by_order(B1_ak, W1, B2_ak, W2):
    """B?_ak: 形状 (年齢階級, 出生順位) の出生数。順位別の分解リストを返す。"""
    B1_ak, B2_ak = np.asarray(B1_ak, float), np.asarray(B2_ak, float)
    W1, W2 = np.asarray(W1, float)[:, None], np.asarray(W2, float)[:, None]
    res = []
    for k in range(B1_ak.shape[1]):
        res.append(decompose(W1[:, 0], B1_ak[:, k] / W1[:, 0], W2[:, 0], B2_ak[:, k] / W2[:, 0]))
    return res

def bootstrap_ci(B1, W1, B2, W2, n=2000, seed=20261115, level=0.95):
    rng = np.random.default_rng(seed)
    B1, B2 = np.asarray(B1, float), np.asarray(B2, float)
    sims = np.empty((n, 2))
    for i in range(n):
        d = decompose_counts(rng.poisson(B1), W1, rng.poisson(B2), W2)
        sims[i] = d["population_effect"], d["rate_effect"]
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return {"population_effect": tuple(np.percentile(sims[:, 0], [lo, hi])),
            "rate_effect": tuple(np.percentile(sims[:, 1], [lo, hi]))}

def sensitivity(B1, B2, denominators: dict):
    """denominators = {'juki_japanese': (W1, W2), 'pref_estimate': (W1, W2)} → 定義別の分解結果"""
    return {k: decompose_counts(B1, w[0], B2, w[1]) for k, w in denominators.items()}
