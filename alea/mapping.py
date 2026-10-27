"""Correspondance automatique des colonnes d'un portefeuille vers le schéma canonique.

Deux signaux sont combinés :
- le sens de l'en-tête, comparé à la description de chaque champ par un modèle d'embeddings
  multilingue (Hugging Face, paraphrase-multilingual-MiniLM-L12-v2) ;
- le profil des valeurs (dates, montants, codes, identifiants, années typiques).
L'affectation finale est optimale (algorithme hongrois). Chaque correspondance porte un score
de confiance ; sous le seuil, elle est marquée « à confirmer » par l'actuaire.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from .normalize import best_date_format, parse_dates

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CONFIRM_THRESHOLD = 0.55

FIELDS = {
    "policy_id": "numéro de police, identifiant du contrat | policy number, contract id",
    "birth_date": "date de naissance de l'assuré | date of birth, birthdate",
    "sex": "sexe ou genre de l'assuré | sex, gender",
    "entry_date": "date d'effet, date de souscription, début du contrat | start date, effective date, inception",
    "exit_date": "date de sortie, date de fin du contrat | exit date, end date, termination date",
    "exit_reason": "motif de sortie, cause de fin : décès, rachat, échéance | exit reason, termination cause",
    "sum_assured": "capital assuré, montant garanti | sum assured, sum insured, benefit amount",
    "product": "produit, garantie, type de contrat | product, cover, plan type",
}
FIELD_LABELS = {
    "policy_id": "Identifiant du contrat", "birth_date": "Date de naissance", "sex": "Sexe",
    "entry_date": "Date d'effet", "exit_date": "Date de sortie", "exit_reason": "Motif de sortie",
    "sum_assured": "Capital assuré", "product": "Produit",
}


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(MODEL_NAME)
    except Exception:  # modèle indisponible : repli lexical
        return None


def semantic_scores(headers: list[str]) -> tuple[np.ndarray, str]:
    """Matrice (en-têtes × champs) de similarité sémantique dans [0, 1]."""
    m = _model()
    descs = list(FIELDS.values())
    if m is not None:
        a = m.encode(headers, normalize_embeddings=True)
        b = m.encode(descs, normalize_embeddings=True)
        return np.clip((a @ b.T + 1) / 2, 0, 1), MODEL_NAME
    sim = np.array([[max(difflib.SequenceMatcher(None, h.lower(), part.strip().lower()).ratio()
                         for part in d.replace("|", ",").split(","))
                     for d in descs] for h in headers])
    return sim, "difflib (repli lexical)"


@dataclass
class Profile:
    date_ratio: float
    median_year: float
    blank_ratio: float
    numeric_ratio: float
    n_unique: int
    unique_ratio: float


def profile(s: pd.Series) -> Profile:
    raw = s.astype(str).str.strip().replace({"nan": "", "NaT": ""})
    nonblank = raw[raw != ""]
    blank_ratio = 1 - len(nonblank) / max(len(raw), 1)
    sample = nonblank.head(2000)
    fmt, ratio = best_date_format(sample)
    median_year = np.nan
    if fmt and ratio > 0.8:
        d = parse_dates(sample, fmt, century_fix=True)
        median_year = float(d.dt.year.median())
    num = pd.to_numeric(sample.str.replace(r"[\s ]", "", regex=True).str.replace(",", "."), errors="coerce")
    return Profile(ratio, median_year, blank_ratio, float(num.notna().mean()) if len(sample) else 0.0,
                   int(nonblank.nunique()), nonblank.nunique() / max(len(nonblank), 1))


def type_score(field: str, p: Profile) -> float:
    is_date = p.date_ratio > 0.8
    y = p.median_year
    if field == "birth_date":
        return 1.0 if is_date and y < 2000 else (0.3 if is_date else 0.0)
    if field == "entry_date":
        return 1.0 if is_date and 2000 <= y <= 2025 and p.blank_ratio < 0.05 else (0.4 if is_date else 0.0)
    if field == "exit_date":
        return 1.0 if is_date and (p.blank_ratio > 0.05 or y >= 2019) else (0.4 if is_date else 0.0)
    if field == "sex":
        return 1.0 if 2 <= p.n_unique <= 5 and not is_date else 0.0
    if field == "exit_reason":
        return 1.0 if 2 <= p.n_unique <= 12 and not is_date and p.numeric_ratio < 0.5 else 0.1
    if field == "sum_assured":
        return 1.0 if p.numeric_ratio > 0.95 and p.n_unique > 20 else 0.0
    if field == "policy_id":
        return 1.0 if p.unique_ratio > 0.9 and not is_date and p.numeric_ratio < 0.95 else 0.2
    if field == "product":
        return 1.0 if 2 <= p.n_unique <= 30 and p.numeric_ratio < 0.5 and not is_date else 0.1
    return 0.0


def propose_mapping(df: pd.DataFrame, w_sem: float = 0.5) -> tuple[pd.DataFrame, str]:
    """Retourne (tableau des correspondances, nom du moteur sémantique)."""
    headers = [str(c) for c in df.columns]
    sem, engine = semantic_scores(headers)
    profiles = [profile(df[c]) for c in df.columns]
    fields = list(FIELDS)
    typ = np.array([[type_score(f, p) for f in fields] for p in profiles])
    score = w_sem * sem + (1 - w_sem) * typ
    r, c = linear_sum_assignment(-score)
    rows = []
    for i, j in zip(r, c):
        rows.append({"champ": fields[j], "libellé": FIELD_LABELS[fields[j]], "colonne source": headers[i],
                     "confiance": round(float(score[i, j]), 3),
                     "sémantique": round(float(sem[i, j]), 3), "profil": round(float(typ[i, j]), 3),
                     "à confirmer": bool(score[i, j] < CONFIRM_THRESHOLD)})
    out = pd.DataFrame(rows).set_index("champ").loc[[f for f in fields if f in {fields[j] for j in c}]].reset_index()
    return out, engine
