"""Études d'expérience : expositions, décès et modèle de mortalité.

- Exposition centrale au risque par âge atteint (âge au dernier anniversaire) et par sexe,
  sur la fenêtre d'observation.
- GLM de Poisson relatif à une table de référence :
  log E[D] = log(E · mu_ref) + b0 + b1·a + sexe,  a = (âge − 50) / 10
  La mortalité estimée est exprimée en pourcentage de la table de référence, avec intervalle
  de confiance à 95 %.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .reference import MAX_AGE

OBS_START, OBS_END = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-01-01")
AGE_MIN, AGE_MAX = 20, 80


def _dec(ts: pd.Series) -> np.ndarray:
    return ((ts - pd.Timestamp("1970-01-01")).dt.days / 365.25 + 1970.0).to_numpy(dtype=float)


def exposures(df: pd.DataFrame, start: pd.Timestamp = OBS_START, end: pd.Timestamp = OBS_END) -> pd.DataFrame:
    """Cellules (sex, age, E, D) à partir de données canoniques nettoyées."""
    s0, s1 = _dec(pd.Series([start]))[0], _dec(pd.Series([end]))[0]
    birth, entry = _dec(df["birth_date"]), _dec(df["entry_date"])
    exit_ = _dec(df["exit_date"])  # NaN si en cours
    death = (df["exit_reason"] == "death").to_numpy()
    a = np.maximum(entry, s0)
    b = np.where(np.isnan(exit_), s1, np.minimum(exit_, s1))
    valid = b > a
    E = {s: np.zeros(MAX_AGE + 1) for s in ("M", "F")}
    D = {s: np.zeros(MAX_AGE + 1) for s in ("M", "F")}
    sex = df["sex"].to_numpy()
    k0 = np.floor(a - birth)
    for j in range(0, 9):
        k = k0 + j
        seg_a = np.maximum(a, birth + k)
        seg_b = np.minimum(b, birth + k + 1)
        e = np.clip(seg_b - seg_a, 0, None) * valid
        ages = np.clip(k, 0, MAX_AGE).astype(int)
        for s in ("M", "F"):
            m = (sex == s) & (e > 0)
            np.add.at(E[s], ages[m], e[m])
    dmask = valid & death & ~np.isnan(exit_) & (exit_ >= s0) & (exit_ < s1)
    dage = np.clip(np.floor(exit_[dmask] - birth[dmask]), 0, MAX_AGE).astype(int)
    for s in ("M", "F"):
        m = sex[dmask] == s
        np.add.at(D[s], dage[m], 1)
    rows = [pd.DataFrame({"sex": s, "age": np.arange(MAX_AGE + 1), "E": E[s], "D": D[s]}) for s in ("M", "F")]
    return pd.concat(rows, ignore_index=True)


def _design(age: np.ndarray, sex: np.ndarray) -> np.ndarray:
    # Log-linéaire en âge + effet sexe : forme robuste quand les décès sont rares aux jeunes âges
    # (un terme quadratique extrapolait mal en dessous de 35 ans).
    a = (age - 50) / 10.0
    f = (sex == "F").astype(float)
    return np.column_stack([np.ones_like(a), a, f])


def fit_relative_glm(cells: pd.DataFrame, ref_mu: dict[str, np.ndarray],
                     age_min: int = AGE_MIN, age_max: int = AGE_MAX) -> dict:
    """Ajuste le GLM relatif. Retourne le modèle et la table estimée (âges age_min-age_max)."""
    c = cells[(cells["age"].between(age_min, age_max)) & (cells["E"] > 0)].copy()
    c["mu_ref"] = [ref_mu[s][a] for s, a in zip(c["sex"], c["age"])]
    X = _design(c["age"].to_numpy(float), c["sex"].to_numpy())
    model = sm.GLM(c["D"].to_numpy(), X, family=sm.families.Poisson(),
                   offset=np.log(c["E"].to_numpy() * c["mu_ref"].to_numpy())).fit()
    out = []
    ages = np.arange(age_min, age_max + 1)
    cov = model.cov_params()
    for s in ("M", "F"):
        Xp = _design(ages.astype(float), np.array([s] * len(ages)))
        eta = Xp @ model.params
        se = np.sqrt(np.einsum("ij,jk,ik->i", Xp, cov, Xp))
        ref = ref_mu[s][ages]
        out.append(pd.DataFrame({"sex": s, "age": ages, "mu_ref": ref, "ratio": np.exp(eta),
                                 "mu": ref * np.exp(eta), "mu_lo": ref * np.exp(eta - 1.96 * se),
                                 "mu_hi": ref * np.exp(eta + 1.96 * se)}))
    table = pd.concat(out, ignore_index=True)
    table = table.merge(cells[["sex", "age", "E", "D"]], on=["sex", "age"], how="left")
    table["crude"] = np.where(table["E"] > 0, table["D"] / table["E"], np.nan)
    expected = float((c["E"] * c["mu_ref"]).sum())
    return {"model": model, "table": table, "deaths": float(c["D"].sum()), "expected_ref": expected,
            "ae_ref": float(c["D"].sum()) / expected if expected else np.nan, "exposure": float(c["E"].sum())}


def to_mu_lookup(table: pd.DataFrame, fallback: dict[str, np.ndarray], col: str = "mu") -> dict[str, np.ndarray]:
    """Table complète 0-MAX_AGE : valeurs estimées sur la plage, référence ajustée ailleurs."""
    res = {}
    for s in ("M", "F"):
        t = table[table["sex"] == s].set_index("age")
        arr = fallback[s].copy()
        lo, hi = t.index.min(), t.index.max()
        arr[lo:hi + 1] = t.loc[lo:hi, col].to_numpy()
        arr[:lo] = fallback[s][:lo] * t.loc[lo, "ratio"]
        arr[hi + 1:] = fallback[s][hi + 1:] * t.loc[hi, "ratio"]
        res[s] = arr
    return res
