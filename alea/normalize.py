"""Mise au format canonique : dates, sexes, motifs de sortie, montants.

Chaque transformation automatique qui modifie une valeur est consignée (journal de
normalisation), pour que l'actuaire puisse la revoir.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y", "%d/%m/%y", "%Y/%m/%d", "%m/%d/%Y"]
EXTRACTION_YEAR = 2025


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def best_date_format(values: pd.Series) -> tuple[str | None, float]:
    vals = values.astype(str).str.strip()
    vals = vals[(vals != "") & (vals != "nan")]
    if vals.empty:
        return None, 0.0
    best, best_ratio = None, 0.0
    for fmt in DATE_FORMATS:
        ratio = pd.to_datetime(vals, format=fmt, errors="coerce").notna().mean()
        if ratio > best_ratio + 1e-9:
            best, best_ratio = fmt, float(ratio)
    return best, best_ratio


def parse_dates(values: pd.Series, fmt: str | None, century_fix: bool = False) -> pd.Series:
    vals = values.astype(str).str.strip().replace({"nan": "", "NaT": ""})
    if fmt is None:
        return pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    d = pd.to_datetime(vals, format=fmt, errors="coerce")
    if century_fix and "%y" in fmt:
        future = d.dt.year > EXTRACTION_YEAR
        d = d.where(~future, d - pd.DateOffset(years=100))
    return d


SEX_MAP = {"m": "M", "h": "M", "homme": "M", "masculin": "M", "male": "M", "man": "M", "1": "M",
           "f": "F", "femme": "F", "feminin": "F", "female": "F", "woman": "F", "2": "F"}
REASON_MAP = {
    "death": ["deces", "decede", "death", "dc", "d", "mort"],
    "lapse": ["rachat", "resiliation", "lapse", "l", "surrender", "annulation"],
    "maturity": ["echeance", "terme", "maturity", "m", "expiration", "fin de contrat"],
    None: ["", "en cours", "in force", "actif", "nan", "vivant"],
}
_REASON_LOOKUP = {v: k for k, vs in REASON_MAP.items() for v in vs}


def normalize(df: pd.DataFrame, mapping: dict[str, str]) -> tuple[pd.DataFrame, list[dict]]:
    """mapping : {champ canonique: colonne source}. Retourne (données canoniques, journal)."""
    log: list[dict] = []
    out = pd.DataFrame(index=df.index)
    out["row"] = np.arange(len(df))
    out["policy_id"] = df[mapping["policy_id"]].astype(str).str.strip()
    for f in ("birth_date", "entry_date", "exit_date"):
        col = df[mapping[f]]
        fmt, ratio = best_date_format(col)
        out[f] = parse_dates(col, fmt, century_fix=(f == "birth_date"))
        log.append({"champ": f, "transformation": f"format de date détecté : {fmt}", "taux de lecture": round(ratio, 4)})
        if f == "birth_date" and fmt and "%y" in fmt:
            log.append({"champ": f, "transformation": "années à deux chiffres : siècle corrigé pour les naissances postérieures à l'extraction", "taux de lecture": None})
    sraw = df[mapping["sex"]].astype(str).str.strip().str.lower().map(_strip_accents)
    out["sex"] = sraw.map(SEX_MAP)
    if set(sraw.unique()) & {"1", "2"}:
        log.append({"champ": "sex", "transformation": "convention supposée : 1 = homme, 2 = femme (à confirmer)", "taux de lecture": None})
    rraw = df[mapping["exit_reason"]].astype(str).str.strip().str.lower().map(_strip_accents)
    out["exit_reason"] = rraw.map(lambda v: _REASON_LOOKUP.get(v, "unknown"))
    unknown = sorted(set(rraw[out["exit_reason"] == "unknown"]))
    if unknown:
        log.append({"champ": "exit_reason", "transformation": f"motifs non reconnus : {unknown[:10]}", "taux de lecture": None})
    out.loc[out["exit_reason"] == "unknown", "exit_reason"] = None
    amt = df[mapping["sum_assured"]].astype(str).str.replace(r"[\s ]", "", regex=True).str.replace(",", ".")
    out["sum_assured"] = pd.to_numeric(amt, errors="coerce")
    out["product"] = df[mapping["product"]].astype(str).str.strip() if "product" in mapping else ""
    return out, log
