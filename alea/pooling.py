"""Mutualisation de marché sans données personnelles.

Chaque assureur exécute Aléa chez lui et ne partage que des agrégats : exposition et nombre
de décès par (sexe, âge). Les cellules trop petites sont supprimées avant partage pour
empêcher toute réidentification. Le marché est la somme des agrégats partagés.
"""
from __future__ import annotations

import pandas as pd

MIN_EXPOSURE = 20.0  # années-personnes minimales par cellule partagée


def shareable_aggregates(cells: pd.DataFrame, insurer: str, min_exposure: float = MIN_EXPOSURE) -> tuple[pd.DataFrame, dict]:
    c = cells[cells["E"] > 0].copy()
    small = c["E"] < min_exposure
    shared = c[~small].copy()
    shared.insert(0, "assureur", insurer)
    info = {"assureur": insurer, "cellules partagées": int((~small).sum()), "cellules supprimées": int(small.sum()),
            "exposition supprimée (années)": round(float(c.loc[small, "E"].sum()), 1),
            "décès supprimés": int(c.loc[small, "D"].sum())}
    return shared[["assureur", "sex", "age", "E", "D"]], info


def market(aggregates: list[pd.DataFrame]) -> pd.DataFrame:
    allc = pd.concat(aggregates, ignore_index=True)
    return allc.groupby(["sex", "age"], as_index=False)[["E", "D"]].sum()


def mask_single_contributor(aggregates: list[pd.DataFrame]) -> tuple[list[pd.DataFrame], dict]:
    """Supprime les cellules (sexe, âge) où un seul assureur contribue.

    Une telle cellule n'est plus un agrégat : c'est la donnée individuelle d'un assureur
    présentée comme étant celle du marché. Elle est retirée pour tous, avant mutualisation.
    """
    allc = pd.concat(aggregates, ignore_index=True)
    n_contrib = allc.groupby(["sex", "age"])["assureur"].nunique()
    single = set(n_contrib[n_contrib < 2].index)
    idx = allc.set_index(["sex", "age"]).index
    info = {"cellules_a_contributeur_unique": len(single),
            "expositions_supprimees (annees)": round(float(allc[idx.isin(single)]["E"].sum()), 1),
            "deces_supprimes": int(allc[idx.isin(single)]["D"].sum())}
    out = []
    for a in aggregates:
        ai = a.set_index(["sex", "age"]).index
        out.append(a[~ai.isin(single)].reset_index(drop=True))
    return out, info
