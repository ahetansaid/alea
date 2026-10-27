"""Tarification d'un contrat temporaire décès (prime pure) selon différentes tables."""
from __future__ import annotations

import numpy as np

from .reference import MAX_AGE


def qx_from_mu(mu: np.ndarray) -> np.ndarray:
    return 1 - np.exp(-np.nan_to_num(mu, nan=10.0))


def term_premium(mu: np.ndarray, age: int, term: int, capital: float, rate: float) -> dict:
    """Prime unique pure et prime annuelle pure (payable d'avance pendant la durée)."""
    q = qx_from_mu(mu)
    v = 1 / (1 + rate)
    tpx, nsp, annuity = 1.0, 0.0, 0.0
    for t in range(term):
        x = min(age + t, MAX_AGE)
        annuity += v ** t * tpx
        nsp += v ** (t + 1) * tpx * q[x]
        tpx *= 1 - q[x]
    return {"prime_unique": capital * nsp, "prime_annuelle": capital * nsp / annuity}


def compare(tables: dict[str, dict[str, np.ndarray]], sex: str, age: int, term: int, capital: float, rate: float):
    rows = []
    for name, mu in tables.items():
        p = term_premium(mu[sex], age, term, capital, rate)
        rows.append({"table": name, **{k: round(v) for k, v in p.items()}})
    return rows
