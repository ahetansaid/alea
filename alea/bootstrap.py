"""Bootstrap paramétrique : propager l'incertitude jusqu'à la table finale.

L'intervalle crédible Gamma seul ne dit rien de l'incertitude sur la table de marché ni sur
K. Ici, chaque itération : 1) rééchantillonne les décès de chaque assureur selon le modèle
ajusté (D* ~ Poisson(E × μ_marché × θ)) ; 2) réajuste le marché, K et la crédibilité ;
3) conserve la table obtenue. Les percentiles 2,5 % / 97,5 % des tables forment un intervalle
de confiance de bout en bout, et la dispersion des τ² donne un intervalle sur K.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import pipeline
from .reference import MAX_AGE, load_who_benin, mu_lookup


def _lambda_cells(cells: pd.DataFrame, market_mu: dict[str, np.ndarray], theta_sex: dict[str, float]) -> np.ndarray:
    return np.array([e * market_mu[s][a] * theta_sex.get(s, 1.0) for e, s, a in zip(cells["E"], cells["sex"], cells["age"])])


def bootstrap_ic(shared: dict[str, pd.DataFrame], target: str, n_iter: int = 200, seed: int = 0) -> dict:
    """Intervalles de bout en bout pour la table cible (modèle global et par bandes)."""
    base_aggs = [c.assign(assureur=k) for k, c in shared.items()]
    mkt = pipeline.market_model(base_aggs)
    base = {k: pipeline.credibility_for(shared, k, mkt["mu"]) for k in shared}
    theta0 = {k: {r["sex"]: float(r["theta"]) for _, r in base[k]["theta"].iterrows()} for k in shared}

    rng = np.random.default_rng(seed)
    mus_glob, mus_bands, taus, ks = [], [], [], []
    for _ in range(n_iter):
        resampled = {}
        for k, c in shared.items():
            c2 = c.copy()
            c2["D"] = rng.poisson(_lambda_cells(c, mkt["mu"], theta0[k]))
            resampled[k] = c2
        aggs2 = [v.assign(assureur=k) for k, v in resampled.items()]
        mkt2 = pipeline.market_model(aggs2)
        cred2 = pipeline.credibility_for(resampled, target, mkt2["mu"])
        mus_glob.append(cred2["mu"])
        mus_bands.append(cred2["mu_bands"])
        taus.append(cred2["K_bands"]["tau2_global"])
        ks.append(cred2["K"]["K"])

    def _pct(mus: list[dict], q: float) -> dict[str, np.ndarray]:
        out = {}
        for s in ("M", "F"):
            stack = np.vstack([m[s][: MAX_AGE + 1] for m in mus])
            out[s] = np.nanpercentile(stack, q, axis=0)
        return out

    return {"mu_glob_lo": _pct(mus_glob, 2.5), "mu_glob_hi": _pct(mus_glob, 97.5),
            "mu_bands_lo": _pct(mus_bands, 2.5), "mu_bands_hi": _pct(mus_bands, 97.5),
            "tau2_ic": (float(np.percentile(taus, 2.5)), float(np.percentile(taus, 97.5))),
            "K_ic": (float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))),
            "n_iter": n_iter, "base": base, "market": mkt}
