"""Contrôle qualité des données de portefeuille.

Contrôles de règles (incohérences certaines) et détection d'anomalies statistiques par
Isolation Forest (profils atypiques). Chaque anomalie porte une action proposée ; l'actuaire
l'accepte ou la rejette. Rien n'est corrigé sans décision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

EXTRACTION_DATE = pd.Timestamp("2025-01-15")
OBS_START = pd.Timestamp("2019-01-01")

RULES = {
    "duplicate": ("Doublon exact d'un autre contrat", "exclure"),
    "unreadable_date": ("Date de naissance ou d'effet illisible", "exclure"),
    "birth_after_entry": ("Naissance postérieure à la date d'effet", "exclure"),
    "impossible_age": ("Âge à l'adhésion impossible (> 100 ans)", "exclure"),
    "exit_before_entry": ("Sortie antérieure à la date d'effet", "exclure"),
    # Exclure ces lignes supprimerait des décès, pas des expositions comparables : biais à la baisse.
    "death_without_date": ("Décès sans date de sortie — l'exclure sous-estimerait la mortalité", "imputer la date"),
    "future_date": ("Date de sortie postérieure à l'extraction", "traiter comme en cours"),
    "invalid_sex": ("Sexe absent ou non reconnu", "exclure"),
    "sum_assured_typo": ("Capital aberrant, probable erreur d'unité (×1000)", "diviser par 1000"),
    "atypical_profile": ("Profil atypique (Isolation Forest) — à examiner", "conserver"),
}


def _issue(df, mask, rule):
    label, action = RULES[rule]
    sub = df.loc[mask, ["row", "policy_id"]].copy()
    sub["contrôle"] = rule
    sub["description"] = label
    sub["action proposée"] = action
    return sub


def detect(df: pd.DataFrame, contamination: float = 0.01, seed: int = 0) -> pd.DataFrame:
    cols = ["policy_id", "birth_date", "sex", "entry_date", "exit_date", "exit_reason", "sum_assured", "product"]
    issues = [_issue(df, df.duplicated(subset=cols, keep="first"), "duplicate")]
    issues.append(_issue(df, df["birth_date"].isna() | df["entry_date"].isna(), "unreadable_date"))
    issues.append(_issue(df, df["birth_date"] > df["entry_date"], "birth_after_entry"))
    entry_age = (df["entry_date"] - df["birth_date"]).dt.days / 365.25
    issues.append(_issue(df, entry_age > 100, "impossible_age"))
    issues.append(_issue(df, df["exit_date"] < df["entry_date"], "exit_before_entry"))
    issues.append(_issue(df, (df["exit_reason"] == "death") & df["exit_date"].isna(), "death_without_date"))
    issues.append(_issue(df, df["exit_date"] > EXTRACTION_DATE, "future_date"))
    issues.append(_issue(df, df["sex"].isna(), "invalid_sex"))

    # Isolation Forest sur des variables de profil
    end = df["exit_date"].where(df["exit_date"] <= EXTRACTION_DATE, EXTRACTION_DATE).fillna(EXTRACTION_DATE)
    feats = pd.DataFrame({
        "entry_age": entry_age.clip(-10, 150),
        "log_sa": np.log10(df["sum_assured"].clip(lower=1)),
        "duration": ((end - df["entry_date"]).dt.days / 365.25).clip(-50, 50),
    }).fillna(0)
    iso = IsolationForest(n_estimators=200, contamination=contamination, random_state=seed)
    outlier = pd.Series(iso.fit_predict(feats) == -1, index=df.index)
    log_sa = feats["log_sa"]
    med = log_sa.median()
    mad = (log_sa - med).abs().median() * 1.4826
    z = (log_sa - med) / (mad if mad > 0 else 1)
    typo = outlier & (z > 3) & (((log_sa - 3) - med).abs() / (mad if mad > 0 else 1) < 3)
    issues.append(_issue(df, typo, "sum_assured_typo"))
    already = pd.concat(issues)["row"].unique()
    info = outlier & ~typo & ~df["row"].isin(already)
    issues.append(_issue(df, info, "atypical_profile"))
    out = pd.concat(issues, ignore_index=True)
    out["accepter"] = True
    return out


def apply(df: pd.DataFrame, issues: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Applique les seules actions acceptées. Retourne (données corrigées, résumé)."""
    acc = issues[issues["accepter"]]
    clean = df.copy()
    excl = set(acc.loc[acc["action proposée"] == "exclure", "row"])
    div = set(acc.loc[acc["action proposée"] == "diviser par 1000", "row"])
    fut = set(acc.loc[acc["action proposée"] == "traiter comme en cours", "row"])
    clean.loc[clean["row"].isin(div), "sum_assured"] /= 1000
    imp = set(acc.loc[acc["action proposée"] == "imputer la date", "row"])
    m_imp = clean["row"].isin(imp)
    # Date imputée au milieu de la période d'observation possible (entre l'entrée en observation et l'extraction)
    start = clean.loc[m_imp, "entry_date"].clip(lower=OBS_START)
    clean.loc[m_imp, "exit_date"] = start + (EXTRACTION_DATE.normalize() - pd.Timedelta(days=15) - start) / 2
    m = clean["row"].isin(fut)
    clean.loc[m, "exit_date"] = pd.NaT
    clean.loc[m, "exit_reason"] = None
    clean = clean[~clean["row"].isin(excl)].reset_index(drop=True)
    return clean, {"lignes initiales": len(df), "exclues": len(excl), "capitaux corrigés": len(div),
                   "dates de décès imputées": len(imp),
                   "remises en cours": len(fut), "lignes retenues": len(clean)}


def evaluate(issues: pd.DataFrame, truth: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Précision et rappel par type d'erreur, sur les erreurs injectées (données synthétiques)."""
    flagged = issues[issues["contrôle"] != "atypical_profile"]
    truth_rows = dict(zip(truth["row"], truth["error_type"]))
    dup_ids = set(df.loc[df["row"].isin(truth.loc[truth["error_type"] == "duplicate", "row"]), "policy_id"])
    rows = []
    for kind in sorted(set(truth["error_type"])):
        t = set(truth.loc[truth["error_type"] == kind, "row"])
        f = flagged[flagged["contrôle"] == kind]
        if kind == "duplicate":
            tp_f = f["policy_id"].isin(dup_ids).sum()
            found = len(set(f["policy_id"]) & dup_ids)
        else:
            tp_f = f["row"].isin(t).sum()
            found = len(set(f["row"]) & t)
        rows.append({"type d'erreur": kind, "injectées": len(t), "signalées": len(f),
                     "précision": round(tp_f / len(f), 3) if len(f) else None,
                     "rappel": round(found / len(t), 3) if t else None})
    all_err = set(truth_rows)
    any_flag = set(flagged["row"])
    dup_rows_ok = set(flagged.loc[(flagged["contrôle"] == "duplicate") & flagged["policy_id"].isin(dup_ids), "row"])
    tp = len((any_flag & all_err) | dup_rows_ok)
    caught = len(all_err & any_flag) + sum(1 for r, k in truth_rows.items() if k == "duplicate" and r not in any_flag
                                           and df.loc[df["row"] == r, "policy_id"].iloc[0] in set(flagged.loc[flagged["contrôle"] == "duplicate", "policy_id"]))
    rows.append({"type d'erreur": "TOTAL", "injectées": len(all_err), "signalées": len(any_flag),
                 "précision": round(tp / len(any_flag), 3) if any_flag else None,
                 "rappel": round(caught / len(all_err), 3) if all_err else None})
    return pd.DataFrame(rows)
