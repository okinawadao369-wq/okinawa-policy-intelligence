"""合成データ（SYNTHETIC — 実統計ではない）による数式検証テスト"""
import numpy as np
from decomposition import decompose_counts, decompose_by_order, bootstrap_ci, sensitivity

# SYNTHETIC: 7年齢階級（15-19..45-49）
W1 = np.array([400, 380, 360, 350, 340, 330, 320.])
W2 = np.array([380, 360, 350, 330, 320, 330, 330.])
B1 = np.array([8, 40, 90, 110, 70, 18, 1.])
B2 = np.array([6, 35, 85, 100, 72, 20, 1.])

def test_exact_additivity():
    d = decompose_counts(B1, W1, B2, W2)
    assert abs(d["total"] - (B2.sum() - B1.sum())) < 1e-9
    assert abs(d["population_effect"] + d["rate_effect"] - d["total"]) < 1e-9

def test_pure_population_change():
    d = decompose_counts(B1, W1, B1 * 1.1, W1 * 1.1)   # 率不変・人口10%増
    assert abs(d["rate_effect"]) < 1e-9 and abs(d["population_effect"] - B1.sum() * 0.1) < 1e-9

def test_pure_rate_change():
    d = decompose_counts(B1, W1, B1 * 0.9, W1)          # 人口不変・率10%減
    assert abs(d["population_effect"]) < 1e-9 and abs(d["rate_effect"] + B1.sum() * 0.1) < 1e-9

def test_symmetry():                                    # 期間を入れ替えると符号だけ反転
    a, b = decompose_counts(B1, W1, B2, W2), decompose_counts(B2, W2, B1, W1)
    assert abs(a["population_effect"] + b["population_effect"]) < 1e-9

def test_birth_order_sums_to_total():
    share1 = np.array([[.9, .1, 0], [.6, .3, .1], [.45, .35, .2], [.3, .4, .3], [.2, .4, .4], [.2, .3, .5], [.1, .3, .6]])
    share2 = share1[:, [0, 1, 2]] * np.array([0.95, 1.0, 1.05]); share2 /= share2.sum(1, keepdims=True)
    parts = decompose_by_order(B1[:, None] * share1, W1, B2[:, None] * share2, W2)
    tot = decompose_counts(B1, W1, B2, W2)
    assert abs(sum(p["rate_effect"] for p in parts) - tot["rate_effect"]) < 1e-9
    assert abs(sum(p["population_effect"] for p in parts) - tot["population_effect"]) < 1e-9

def test_bootstrap_ci_contains_point_and_widens_for_small_counts():
    d = decompose_counts(B1, W1, B2, W2)
    ci = bootstrap_ci(B1, W1, B2, W2, n=800)
    assert ci["rate_effect"][0] <= d["rate_effect"] <= ci["rate_effect"][1]
    small = bootstrap_ci(B1 / 20, W1 / 20, B2 / 20, W2 / 20, n=800)
    rel = lambda c, s: (c[1] - c[0]) / s
    assert rel(small["rate_effect"], B1.sum() / 20) > rel(ci["rate_effect"], B1.sum())

def test_sensitivity_runs():
    s = sensitivity(B1, B2, {"a": (W1, W2), "b": (W1 * 1.02, W2 * 0.99)})
    assert set(s) == {"a", "b"}
