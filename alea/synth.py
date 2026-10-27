"""Générateur de portefeuilles d'assureurs FICTIFS, avec vérité connue.

Chaque portefeuille est simulé à partir de la mortalité OMS du Bénin, modifiée par un effet
de sélection (les assurés sont en meilleure santé que la population, surtout jeunes) et par
un multiplicateur propre à l'assureur. On injecte ensuite des erreurs réalistes, dont la
position est enregistrée : cela permet de mesurer ce que le prototype détecte et reconstruit.

Aucune donnée réelle n'est utilisée.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .reference import MAX_AGE, load_who_benin, mu_lookup

OBS_START, OBS_END = 2019.0, 2025.0  # fenêtre d'observation [01/01/2019, 31/12/2024]
EXTRACTION_DATE = pd.Timestamp("2025-01-15")


@dataclass
class InsurerSpec:
    key: str
    name: str
    n_policies: int
    multiplier: float  # mortalité de l'assureur relative à la table assurée « type »
    share_male: float
    style: str  # format d'export : alpha | beta | gamma
    seed: int
    shape_tilt: float = 0.0  # divergence de forme : <0 = jeune meilleur marché, >0 = jeune plus risqué


INSURERS = [
    InsurerSpec("alpha", "Assureur Alpha (fictif)", 40_000, 0.95, 0.60, "alpha", 11),
    InsurerSpec("beta", "Assureur Bêta (fictif)", 15_000, 1.05, 0.55, "beta", 22),
    InsurerSpec("gamma", "Assureur Gamma (fictif)", 2_500, 1.20, 0.45, "gamma", 33),
    InsurerSpec("delta", "Assureur Delta (fictif)", 8_000, 1.00, 0.50, "beta", 44, shape_tilt=0.45),
]

ERROR_RATES = {
    "duplicate": 0.005,
    "birth_after_entry": 0.003,
    "impossible_age": 0.003,
    "exit_before_entry": 0.003,
    "death_without_date": 0.002,
    "sum_assured_typo": 0.004,
    "invalid_sex": 0.003,
    "future_date": 0.003,
}


def selection_factor(age: np.ndarray) -> np.ndarray:
    """Effet de sélection : 55 % de la mortalité de population à 20 ans, 90 % à 80 ans."""
    return 0.55 + 0.35 * np.clip((age - 20) / 60.0, 0, 1)


def true_mu(spec: InsurerSpec) -> dict[str, np.ndarray]:
    ref = mu_lookup(load_who_benin())
    ages = np.arange(MAX_AGE + 1)
    tilt = np.exp(spec.shape_tilt * (ages - 50) / 10.0) if spec.shape_tilt else 1.0
    return {s: ref[s] * selection_factor(ages) * spec.multiplier * tilt for s in ("M", "F")}


def _to_date(y: np.ndarray) -> pd.Series:
    return pd.to_datetime("1970-01-01") + pd.to_timedelta(np.round((y - 1970.0) * 365.25), unit="D")


def simulate(spec: InsurerSpec) -> pd.DataFrame:
    rng = np.random.default_rng(spec.seed)
    mu = true_mu(spec)
    n = spec.n_policies
    entry = rng.uniform(2005.0, 2024.5, n)
    entry_age = np.clip(rng.normal(38, 10, n), 18, 70)
    birth = entry - entry_age
    sex = np.where(rng.random(n) < spec.share_male, "M", "F")
    term = rng.integers(5, 21, n).astype(float)
    product = rng.choice(["Temporaire décès", "Mixte", "Prévoyance emprunteur"], n, p=[0.5, 0.3, 0.2])
    sum_assured = np.round(np.exp(rng.normal(np.log(2_000_000), 0.6, n)), -3)
    lapse = 0.06

    exit_t = np.full(n, np.nan)
    reason = np.empty(n, dtype=object)
    for i in range(n):
        t, end = entry[i], min(entry[i] + term[i], OBS_END)
        tbl = mu[sex[i]]
        done = False
        while t < end:
            age_int = int(np.floor(t - birth[i]))
            seg_end = min(birth[i] + age_int + 1, end)
            h_d = tbl[min(age_int, MAX_AGE)]
            h = h_d + lapse
            tau = rng.exponential(1.0 / h)
            if t + tau < seg_end:
                exit_t[i] = t + tau
                reason[i] = "death" if rng.random() < h_d / h else "lapse"
                done = True
                break
            t = seg_end
        if not done and entry[i] + term[i] <= OBS_END:
            exit_t[i], reason[i] = entry[i] + term[i], "maturity"
    keep = np.isnan(exit_t) | (exit_t >= OBS_START)  # extraction : contrats vivants en 2019-2024
    df = pd.DataFrame({
        "policy_id": [f"{spec.key[:1].upper()}{i:06d}" for i in range(n)],
        "birth_date": _to_date(birth), "sex": sex, "entry_date": _to_date(entry),
        "exit_date": _to_date(exit_t), "exit_reason": reason, "sum_assured": sum_assured, "product": product,
    })[keep].reset_index(drop=True)
    df.loc[df["exit_reason"].isna(), "exit_date"] = pd.NaT
    return df


def inject_errors(df: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Injecte des erreurs ; retourne (données erronées, vérité = (policy_id, rang, type))."""
    rng = np.random.default_rng(seed + 1000)
    df = df.copy()
    df["_uid"] = np.arange(len(df))
    used: set[int] = set()
    truth = []

    def pick(k: int, pool: np.ndarray) -> np.ndarray:
        pool = np.array([p for p in pool if p not in used])
        k = min(k, len(pool))
        sel = rng.choice(pool, k, replace=False) if k else np.array([], dtype=int)
        used.update(sel.tolist())
        return sel

    n = len(df)
    allidx = np.arange(n)
    for kind, rate in ERROR_RATES.items():
        k = max(1, int(round(rate * n)))
        if kind == "duplicate":
            continue
        if kind == "birth_after_entry":
            idx = pick(k, allidx)
            df.loc[idx, "birth_date"] = df.loc[idx, "entry_date"] + pd.to_timedelta(rng.integers(30, 3000, len(idx)), unit="D")
        elif kind == "impossible_age":
            idx = pick(k, allidx)
            df.loc[idx, "birth_date"] = df.loc[idx, "birth_date"] - pd.DateOffset(years=100)
        elif kind == "exit_before_entry":
            idx = pick(k, np.where(df["exit_date"].notna())[0])
            df.loc[idx, "exit_date"] = df.loc[idx, "entry_date"] - pd.to_timedelta(rng.integers(30, 2000, len(idx)), unit="D")
        elif kind == "death_without_date":
            idx = pick(k, np.where(df["exit_reason"] == "death")[0])
            df.loc[idx, "exit_date"] = pd.NaT
        elif kind == "sum_assured_typo":
            idx = pick(k, allidx)
            df.loc[idx, "sum_assured"] = df.loc[idx, "sum_assured"] * 1000
        elif kind == "invalid_sex":
            idx = pick(k, allidx)
            df.loc[idx, "sex"] = "?"
        elif kind == "future_date":
            idx = pick(k, allidx)
            df.loc[idx, "exit_date"] = pd.to_datetime("2030-06-30")
            df.loc[idx, "exit_reason"] = "maturity"
        truth += [(int(i), kind) for i in idx]
    # doublons : copies exactes de lignes saines, ajoutées au fichier
    kdup = max(1, int(round(ERROR_RATES["duplicate"] * n)))
    dup_src = pick(kdup, allidx)
    dups = df.loc[dup_src].copy()
    dups["_dup"] = True
    df["_dup"] = False
    df = pd.concat([df, dups], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)  # ordre aléatoire
    bad = {u: k for u, k in truth}
    rows = []
    for row, (uid, isdup) in enumerate(zip(df["_uid"], df["_dup"])):
        if isdup:
            rows.append((row, "duplicate"))
        elif uid in bad:
            rows.append((row, bad[uid]))
    t = pd.DataFrame(rows, columns=["row", "error_type"])
    return df.drop(columns=["_uid", "_dup"]), t


# ---------------------------------------------------------------- formats d'export
REASONS = {
    "alpha": {"death": "DECES", "lapse": "RACHAT", "maturity": "ECHEANCE", None: ""},
    "beta": {"death": "Décès", "lapse": "Rachat", "maturity": "Terme", None: "En cours"},
    "gamma": {"death": "D", "lapse": "L", "maturity": "M", None: ""},
}
SEXES = {"alpha": {"M": "M", "F": "F"}, "beta": {"M": "H", "F": "F"}, "gamma": {"M": "1", "F": "2"}}
COLUMNS = {
    "alpha": ["police", "date_naissance", "sexe", "date_effet", "date_sortie", "motif_sortie", "capital_assure", "produit"],
    "beta": ["N° Contrat", "Date de Naissance", "Genre", "Date souscription", "Date fin", "Cause fin", "Capital", "Garantie"],
    "gamma": ["policy_no", "DOB", "gender", "start", "exit", "exit_code", "sum_insured", "cover"],
}
DATEFMT = {"alpha": "%Y-%m-%d", "beta": "%d/%m/%Y", "gamma": "%d-%m-%y"}


def export(df: pd.DataFrame, style: str, path: Path) -> None:
    out = pd.DataFrame()
    fmt = DATEFMT[style]
    vals = [
        df["policy_id"],
        df["birth_date"].dt.strftime(fmt),
        df["sex"].map(lambda s: SEXES[style].get(s, s)),
        df["entry_date"].dt.strftime(fmt),
        df["exit_date"].dt.strftime(fmt).fillna(""),
        df["exit_reason"].map(lambda r: REASONS[style].get(r if isinstance(r, str) else None, "")),
        df["sum_assured"].map(lambda v: f"{int(v):,}".replace(",", " ") if style == "beta" else str(int(v))),
        df["product"],
    ]
    for col, v in zip(COLUMNS[style], vals):
        out[col] = v.to_numpy()
    if style == "beta":
        out.to_csv(path, sep=";", index=False, encoding="cp1252")
    else:
        out.to_csv(path, index=False, encoding="utf-8")


def generate_all(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for spec in INSURERS:
        clean = simulate(spec)
        dirty, truth = inject_errors(clean, spec.seed)
        fname = f"portefeuille_{spec.key}.csv"
        export(dirty, spec.style, out_dir / fname)
        truth.to_csv(out_dir / f"verite_erreurs_{spec.key}.csv", index=False)
        mu = true_mu(spec)
        pd.DataFrame({"age": np.arange(MAX_AGE + 1), "mu_M": mu["M"], "mu_F": mu["F"]}).to_csv(
            out_dir / f"verite_mortalite_{spec.key}.csv", index=False)
        manifest[spec.key] = {"name": spec.name, "file": fname, "rows": len(dirty),
                              "injected_errors": int(len(truth)), "multiplier": spec.multiplier,
                              "shape_tilt": spec.shape_tilt}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
