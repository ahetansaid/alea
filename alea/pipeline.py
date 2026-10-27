"""Enchaînement des étapes pour un portefeuille, utilisé par l'interface et l'évaluation."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import numpy as np
import pandas as pd

from . import credibility, experience, mapping, normalize, pooling, quality
from .reference import load_who_benin, mu_lookup


def read_portfolio(data: bytes) -> pd.DataFrame:
    """Lit un CSV d'origine inconnue : encodage et séparateur détectés."""
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        sep = csv.Sniffer().sniff(text[:5000], delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)


def auto_run(path: Path, insurer: str) -> dict:
    """Exécution automatique (actions proposées acceptées), comme le ferait chaque assureur chez lui."""
    raw = read_portfolio(Path(path).read_bytes())
    m, engine = mapping.propose_mapping(raw)
    mp = dict(zip(m["champ"], m["colonne source"]))
    canon, log = normalize.normalize(raw, mp)
    issues = quality.detect(canon)
    clean, summary = quality.apply(canon, issues)
    cells = experience.exposures(clean)
    return {"insurer": insurer, "raw": raw, "mapping": m, "engine": engine, "canon": canon, "log": log,
            "issues": issues, "clean": clean, "summary": summary, "cells": cells}


def market_model(aggregates: list[pd.DataFrame], mask: bool = True) -> dict:
    ref = mu_lookup(load_who_benin())
    mask_info = None
    if mask:
        aggregates, mask_info = pooling.mask_single_contributor(aggregates)
    mkt_cells = pooling.market(aggregates)
    if mkt_cells.empty or mkt_cells["D"].sum() <= 0:
        raise ValueError("Marché dégénéré : plus aucune cellule commune après masquage des contributeurs "
                         "uniques (ou aucun décès mutualisé). Abaisser le seuil d'exposition ou ajouter "
                         "des assureurs.")
    fit = experience.fit_relative_glm(mkt_cells, ref)
    return {"cells": mkt_cells, "fit": fit, "mu": experience.to_mu_lookup(fit["table"], ref), "mask_info": mask_info}


def credibility_for(insurer_cells: dict[str, pd.DataFrame], target: str, market_mu: dict[str, np.ndarray]) -> dict:
    per = {k: credibility.expected_deaths(c, market_mu) for k, c in insurer_cells.items()}
    k = credibility.estimate_k(list(per.values()))
    theta = credibility.apply_credibility(per[target], k["K"])
    bands_own = {kk: credibility.expected_deaths_by_band(c, market_mu) for kk, c in insurer_cells.items()}
    kb = credibility.estimate_k_pooled(list(bands_own.values()), k["tau2"])
    k_by_band = {b["band"]: b["K"] for b in kb["per_band"]}
    theta_bands = credibility.apply_credibility_bands(bands_own[target], k_by_band, theta)
    return {"K": k, "theta": theta, "mu": credibility.credible_table(theta, market_mu), "per_insurer": per,
            "K_bands": kb, "theta_bands": theta_bands, "mu_bands": credibility.credible_table_bands(theta_bands, market_mu),
            "bands_own": bands_own}


def credibility_loo(insurer_cells: dict[str, pd.DataFrame], target: str) -> dict:
    """Version « leave-one-out » : le marché de référence est ajusté sans l'assureur évalué,
    qui autrement se crédibilise lui-même (biais d'auto-contamination, sensible quand un
    assureur domine le marché)."""
    others = {k: c for k, c in insurer_cells.items() if k != target}
    if not others:
        raise ValueError("crédibilité leave-one-out : il faut au moins deux assureurs")
    aggs = [c.assign(assureur=k) for k, c in others.items()]
    mkt = market_model(aggs)
    return credibility_for(insurer_cells, target, mkt["mu"]) | {"market_loo": mkt}


def weighted_log_error(mu_est: dict, mu_true: dict, weights: pd.DataFrame, age_min=25, age_max=70) -> float:
    w = weights[weights["age"].between(age_min, age_max)]
    w = w[w["E"] > 0]
    if w.empty:
        return float("nan")
    est = np.vstack([mu_est["M"], mu_est["F"]])
    tru = np.vstack([mu_true["M"], mu_true["F"]])
    rows = (w["sex"].to_numpy() != "M").astype(int)
    ages = w["age"].to_numpy()
    e = w["E"].to_numpy()
    ratio = np.abs(np.log(est[rows, ages] / tru[rows, ages]))
    return float((e * ratio).sum() / e.sum())
