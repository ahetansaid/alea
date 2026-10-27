"""Tables de mortalité de référence.

La table OMS du Bénin est publiée par groupes d'âge (nqx). On la convertit en forces de
mortalité par âge entier : interpolation log-linéaire entre les milieux de groupes, puis
extrapolation de Gompertz au-delà de 85 ans.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"
MAX_AGE = 105
AGES = np.arange(0, MAX_AGE + 1)


def _group_bounds(label: str) -> tuple[int, int]:
    if label.endswith("PLUS"):
        lo = int(label.replace("PLUS", ""))
        return lo, MAX_AGE + 1
    lo, hi = label.split("-")
    lo, hi = int(lo), int(hi)
    # « 00-01 » couvre [0,1) ; « 01-04 » couvre [1,5) ; « 05-09 » couvre [5,10)
    return lo, (hi if lo == 0 else hi + 1)


def load_who_benin() -> pd.DataFrame:
    """Retourne un DataFrame (sex, age, mu, qx) pour les âges 0 à MAX_AGE."""
    raw = pd.read_csv(DATA_DIR / "who_benin_2023_nqx.csv", dtype={"age_group": str})
    out = []
    for sex, g in raw.groupby("sex"):
        mids, logmu = [], []
        for _, r in g.iterrows():
            lo, hi = _group_bounds(r["age_group"])
            if r["age_group"].endswith("PLUS"):
                continue  # 85+ : nqx = 1 par construction, inutilisable
            n = hi - lo
            mu = -np.log(1.0 - r["nqx"]) / n
            mids.append((lo + hi) / 2.0)
            logmu.append(np.log(mu))
        mids, logmu = np.array(mids), np.array(logmu)
        order = np.argsort(mids)
        mids, logmu = mids[order], logmu[order]
        x = AGES + 0.5
        lm = np.interp(x, mids, logmu)
        # Gompertz au-delà du dernier milieu : pente ajustée sur 60-84 ans
        sel = mids >= 60
        slope, intercept = np.polyfit(mids[sel], logmu[sel], 1)
        beyond = x > mids[-1]
        lm[beyond] = logmu[-1] + slope * (x[beyond] - mids[-1])
        mu = np.exp(lm)
        out.append(pd.DataFrame({"sex": sex, "age": AGES, "mu": mu, "qx": 1 - np.exp(-mu)}))
    return pd.concat(out, ignore_index=True)


def load_regulatory() -> pd.DataFrame | None:
    """Table réglementaire (CIMA) si l'utilisateur l'a fournie, sinon None."""
    path = DATA_DIR / "cima.csv"
    if not path.exists():
        return None
    t = pd.read_csv(path)
    t["mu"] = -np.log(1 - t["qx"].clip(upper=0.999999))
    return t[["sex", "age", "mu", "qx"]]


def mu_lookup(table: pd.DataFrame) -> dict[str, np.ndarray]:
    """{sexe: tableau des forces de mortalité indexé par âge}."""
    res = {}
    for sex, g in table.groupby("sex"):
        arr = np.full(MAX_AGE + 1, np.nan)
        arr[g["age"].to_numpy()] = g["mu"].to_numpy()
        res[sex] = arr
    return res
