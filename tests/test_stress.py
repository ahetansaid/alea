"""Tests de contrainte : marchés dégénérés, zéro décès, seuils extrêmes, équivalence vectorisation."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alea import bootstrap, credibility, pipeline, pooling  # noqa: E402


def cells_df(insurer, pairs):
    return pd.DataFrame([{"assureur": insurer, "sex": s, "age": a, "E": e, "D": d} for s, a, e, d in pairs])


def test_expected_deaths_vectorized_matches_loop():
    rng = np.random.default_rng(7)
    ages = np.arange(20, 81)
    mu = {"M": 0.001 + 1e-5 * ages, "F": 0.0008 + 8e-6 * ages}
    mu = {s: np.pad(mu[s], (20, 25), mode="edge") for s in ("M", "F")}
    c = pd.DataFrame({"sex": rng.choice(["M", "F"], 300), "age": rng.integers(20, 81, 300),
                      "E": rng.random(300) * 100, "D": rng.integers(0, 3, 300)})
    loop = c[c["age"].between(20, 80)].copy()
    loop["Ep"] = [e * mu[s][a] for e, s, a in zip(loop["E"], loop["sex"], loop["age"])]
    ref = loop.groupby("sex", as_index=False)[["D", "Ep", "E"]].sum()
    got = credibility.expected_deaths(c, mu)
    assert np.allclose(ref.sort_values("sex")[["D", "Ep"]], got.sort_values("sex")[["D", "Ep"]])


def test_weighted_log_error_vectorized_matches_loop():
    rng = np.random.default_rng(3)
    ages = np.arange(106)
    mu_est = {s: np.exp(-6 + 0.06 * (ages / 20)) * (1 + 0.1 * rng.random()) for s in ("M", "F")}
    mu_true = {s: np.exp(-6 + 0.06 * (ages / 20)) for s in ("M", "F")}
    w = pd.DataFrame({"sex": rng.choice(["M", "F"], 200), "age": rng.integers(25, 71, 200),
                      "E": rng.random(200) * 50})
    num = den = 0.0
    for s, a, e in zip(w["sex"], w["age"], w["E"]):
        if e <= 0:
            continue
        num += e * abs(np.log(mu_est[s][a] / mu_true[s][a]))
        den += e
    assert abs(pipeline.weighted_log_error(mu_est, mu_true, w) - num / den) < 1e-12


def test_market_unique_contributor_guard():
    a = cells_df("A", [("M", 40, 100.0, 2.0), ("F", 50, 80.0, 1.0)])
    try:
        pipeline.market_model([a])
        assert False, "un marché à un seul assureur doit être refusé après masquage"
    except ValueError as exc:
        assert "dégénéré" in str(exc)


def test_market_zero_deaths_guard():
    a = cells_df("A", [("M", 40, 100.0, 0.0)])
    b = cells_df("B", [("M", 40, 120.0, 0.0)])
    try:
        pipeline.market_model([a, b])
        assert False, "aucun décès mutualisé doit être refusé"
    except ValueError:
        pass


def test_shareable_aggregates_extreme_threshold():
    c = pd.DataFrame({"sex": ["M", "F"], "age": [40, 50], "E": [100.0, 50.0], "D": [2.0, 1.0]})
    shared, info = pooling.shareable_aggregates(c, "A", min_exposure=1000)
    assert shared.empty and info["cellules supprimées"] == 2 and info["décès supprimés"] == 3


def test_credibility_zero_deaths():
    own = pd.DataFrame({"sex": ["M", "F"], "D": [0.0, 0.0], "Ep": [80.0, 120.0], "E": [8000.0, 12000.0]})
    out = credibility.apply_credibility(own, K=50)
    assert np.all(out["theta"] < 1) and np.isfinite(out[["theta_lo", "theta_hi"]].to_numpy()).all()


def test_expected_deaths_filters_outside_window():
    mu = {s: np.full(106, 0.01) for s in ("M", "F")}
    c = pd.DataFrame({"sex": ["M", "M"], "age": [10, 95], "E": [500.0, 500.0], "D": [1.0, 1.0]})
    assert credibility.expected_deaths(c, mu).empty


def test_mask_no_removal_when_all_shared():
    a = cells_df("A", [("M", 40, 100.0, 2.0), ("M", 41, 90.0, 1.0)])
    b = cells_df("B", [("M", 40, 120.0, 3.0), ("M", 41, 80.0, 1.0)])
    masked, info = pooling.mask_single_contributor([a, b])
    assert info["cellules_a_contributeur_unique"] == 0
    assert sum(len(m) for m in masked) == 4


def test_estimate_k_identical_insurers_stable():
    per = [pd.DataFrame({"sex": ["M", "F"], "D": [10.0, 8.0], "Ep": [500.0, 400.0], "E": [50000.0, 40000.0]})
           for _ in range(3)]
    k = credibility.estimate_k(per)
    assert np.isfinite(k["K"]) and k["K"] > 0 and k["tau2"] > 0


def test_credible_table_missing_sex_falls_back_to_market():
    theta = pd.DataFrame({"sex": ["M"], "theta": [1.3]})
    market = {s: np.full(106, 0.01) for s in ("M", "F")}
    mu = credibility.credible_table(theta, market)
    assert np.allclose(mu["M"], 0.013)
    assert np.array_equal(mu["F"], market["F"])


def test_bootstrap_smoke_small_market():
    rng = np.random.default_rng(11)
    shared = {}
    for name in ("A", "B", "C"):
        rows = []
        for s in ("M", "F"):
            for a in range(25, 76, 5):
                e = 60.0 + rng.random() * 80
                rows.append({"sex": s, "age": a, "E": e, "D": float(rng.poisson(e * 0.01))})
        shared[name] = pd.DataFrame(rows)
    out = bootstrap.bootstrap_ic(shared, "A", n_iter=3, seed=1)
    assert out["n_iter"] == 3
    for s in ("M", "F"):
        assert np.all(out["mu_glob_lo"][s] <= out["mu_glob_hi"][s] + 1e-12)
        assert np.all(out["mu_bands_lo"][s] <= out["mu_bands_hi"][s] + 1e-12)
    lo, hi = out["K_ic"]
    assert lo <= hi and lo > 0
