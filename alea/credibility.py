"""Crédibilité : combiner l'expérience propre d'un assureur et celle du marché.

Modèle Poisson-Gamma sur le rapport « décès observés / décès attendus selon la table de
marché » (θ). Pour un assureur et un sexe :
    D ~ Poisson(θ · Ep),   θ ~ Gamma(K, K)  (moyenne 1, variance 1/K)
    θ̂ = (D + K) / (Ep + K) = Z · D/Ep + (1 − Z) · 1,   Z = Ep / (Ep + K)
K mesure l'hétérogénéité réelle entre assureurs ; il est estimé sur les données mutualisées
(méthode des moments de Bühlmann), pas fixé à la main.
La table de l'assureur vaut θ̂ × table de marché, avec un intervalle crédible à 95 %.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

AGE_MIN, AGE_MAX = 20, 80


def _ep_matrix(c: pd.DataFrame, mu: dict[str, np.ndarray]) -> np.ndarray:
    mus = np.vstack([mu["M"], mu["F"]])
    rows = (c["sex"].to_numpy() != "M").astype(int)
    return c["E"].to_numpy() * mus[rows, c["age"].to_numpy()]


def expected_deaths(cells: pd.DataFrame, mu: dict[str, np.ndarray], age_min=AGE_MIN, age_max=AGE_MAX) -> pd.DataFrame:
    c = cells[cells["age"].between(age_min, age_max)].copy()
    c["Ep"] = _ep_matrix(c, mu)
    return c.groupby("sex", as_index=False)[["D", "Ep", "E"]].sum()


def estimate_k(per_insurer: list[pd.DataFrame], k_max: float = 1e4) -> dict:
    """Estimateur de Bühlmann-Straub de la variance entre assureurs.

    Poids w_i = décès attendus ; sous Poisson, la variance intra vaut m / w_i.
    tau² = [Σ w_i (r_i − m)² − (n − 1) m] / [w − Σ w_i² / w]
    """
    obs = pd.concat(per_insurer, ignore_index=True)
    obs = obs[obs["Ep"] > 0]
    r = (obs["D"] / obs["Ep"]).to_numpy()
    w = obs["Ep"].to_numpy()
    n, W = len(w), w.sum()
    m = float((w * r).sum() / W)
    num = float((w * (r - m) ** 2).sum() - (n - 1) * m)
    den = float(W - (w ** 2).sum() / W)
    tau2 = max(num / den if den > 0 else 0.0, 1.0 / k_max)
    return {"K": m / tau2, "tau2": tau2, "theta_mean": m, "n_cells": int(n)}


def apply_credibility(own: pd.DataFrame, K: float) -> pd.DataFrame:
    out = own.copy()
    out["theta_obs"] = out["D"] / out["Ep"]
    out["Z"] = out["Ep"] / (out["Ep"] + K)
    out["theta"] = (out["D"] + K) / (out["Ep"] + K)
    out["theta_lo"] = stats.gamma.ppf(0.025, a=K + out["D"], scale=1 / (K + out["Ep"]))
    out["theta_hi"] = stats.gamma.ppf(0.975, a=K + out["D"], scale=1 / (K + out["Ep"]))
    return out


def credible_table(theta: pd.DataFrame, market_mu: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Table de marché × θ̂. Sexe sans expérience propre (portefeuille sans hommes ni femmes
    dans la fenêtre d'âge) : θ = 1, on garde la table de marché telle quelle."""
    res = {}
    for s in ("M", "F"):
        row = theta.loc[theta["sex"] == s, "theta"]
        res[s] = market_mu[s] * (float(row.iloc[0]) if len(row) else 1.0)
    return res


# ---------------------------------------------------------------- bandes d'âge
# Un seul θ par sexe suppose que l'assureur s'écarte du marché de la même façon à tous les
# âges. Les bandes autorisent un niveau différent par tranche (jeunes vs âgés).
BANDS = [(20, 34), (35, 49), (50, 64), (65, 80)]
MIN_BAND_EP = 20.0  # en dessous de 20 décès attendus dans la bande, repli sur le θ global


def band_of(age: pd.Series | np.ndarray) -> pd.Series:
    labels = [f"{lo}-{hi}" for lo, hi in BANDS]
    edges = [lo for lo, _ in BANDS] + [BANDS[-1][1] + 1]
    return pd.Series(pd.cut(np.asarray(age, dtype=float), edges, right=False, labels=labels))


def expected_deaths_by_band(cells: pd.DataFrame, mu: dict[str, np.ndarray],
                            age_min=AGE_MIN, age_max=AGE_MAX) -> pd.DataFrame:
    c = cells[cells["age"].between(age_min, age_max)].copy()
    c["Ep"] = _ep_matrix(c, mu)
    c["band"] = band_of(c["age"])
    return c.groupby(["sex", "band"], observed=True)[["D", "Ep", "E"]].sum().reset_index()


def estimate_k_pooled(per_insurer_bands: list[pd.DataFrame], tau2_global: float) -> dict:
    """τ² estimé bande par bande (méthode des moments restreinte aux assureurs de la bande),
    avec repli sur le τ² global si l'estimation bande est instable ou plus petite — le décompte
    Poisson intra déduit (n_b − 1)·m pénalise les bandes pauvres et gonflerait K.
    Convention identique au cas global : K = moyenne pondérée / τ²."""
    obs = pd.concat(per_insurer_bands, ignore_index=True)
    obs = obs[obs["Ep"] > 0].copy()
    obs["band"] = obs["band"].astype("category")

    def _tau2(sub: pd.DataFrame) -> float | None:
        if sub["sex"].nunique() < 2 or len(sub) < 4:  # ≥ 2 assureurs × 2 sexes
            return None
        r = (sub["D"] / sub["Ep"]).to_numpy()
        w = sub["Ep"].to_numpy()
        n, W = len(w), w.sum()
        m = float((w * r).sum() / W)
        num = float((w * (r - m) ** 2).sum() - (n - 1) * m)
        den = float(W - (w ** 2).sum() / W)
        if den <= 0:
            return None
        return max(num / den, 0.0)

    per_band = []
    for b in obs["band"].cat.categories:
        sub = obs[obs["band"] == b]
        w = sub["Ep"].to_numpy()
        m_b = float((w * (sub["D"] / sub["Ep"]).to_numpy()).sum() / w.sum())
        t = _tau2(sub)
        source = "bande"
        if t is None or t < tau2_global:
            t, source = tau2_global, "global"
        t = max(t, 1e-4)
        per_band.append({"band": str(b), "Ep_moyen": float(w.mean()), "tau2": t, "source_tau2": source,
                         "K": m_b / t})
    return {"tau2_global": tau2_global, "n_cells": int(len(obs)), "per_band": per_band}


def apply_credibility_bands(own_bands: pd.DataFrame, k_by_band: dict[str, float],
                            global_theta: pd.DataFrame) -> pd.DataFrame:
    """θ par (sexe, bande), avec repli sur le θ global du sexe si la bande est trop pauvre."""
    out = own_bands[own_bands["Ep"] > 0].copy()
    if out.empty:
        return out.assign(K=[], Z=[], theta=[], theta_obs=[], theta_lo=[], theta_hi=[],
                          repli=[], theta_retenu=[])
    out["K"] = [k_by_band.get(str(b), np.inf) for b in out["band"]]
    out["theta_obs"] = out["D"] / out["Ep"]
    out["Z"] = out["Ep"] / (out["Ep"] + out["K"])
    out["theta"] = (out["D"] + out["K"]) / (out["Ep"] + out["K"])
    a = out["K"] + out["D"]
    scale = 1.0 / (out["K"] + out["Ep"])
    out["theta_lo"] = stats.gamma.ppf(0.025, a=a, scale=scale)
    out["theta_hi"] = stats.gamma.ppf(0.975, a=a, scale=scale)
    g = global_theta.set_index("sex")
    out["repli"] = out["Ep"] < MIN_BAND_EP
    out["theta_retenu"] = np.where(out["repli"], out["sex"].map(g["theta"]), out["theta"])
    return out


def credible_table_bands(theta_bands: pd.DataFrame, market_mu: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Table du marché × θ(âge), θ interpolé linéairement entre milieux de bandes
    (constante aux extrémités) pour éviter les marches d'escalier."""
    mids = {f"{lo}-{hi}": (lo + hi) / 2.0 for lo, hi in BANDS}
    ages = np.arange(AGE_MIN, AGE_MAX + 1, dtype=float)
    res = {}
    for s in ("M", "F"):
        t = theta_bands[theta_bands["sex"] == s]
        arr = market_mu[s].copy()
        if not t.empty:
            x = np.array([mids[str(b)] for b in t["band"]])
            y = t["theta_retenu"].to_numpy(float)
            order = np.argsort(x)
            arr[int(AGE_MIN):int(AGE_MAX) + 1] *= np.interp(ages, x[order], y[order])
        res[s] = arr
    return res
