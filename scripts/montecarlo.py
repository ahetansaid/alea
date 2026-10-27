"""Évaluation Monte-Carlo : erreur moyenne de chaque méthode selon la taille de l'assureur.

Un seul tirage ne dit pas si une méthode est meilleure ou chanceuse. On simule ici R marchés
de 6 assureurs fictifs (données propres, sans erreurs injectées) et on mesure, pour chacun,
l'écart entre la table estimée et la vraie mortalité. Produit reports/montecarlo.md.

Usage : python scripts/montecarlo.py [R]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alea import experience, pipeline, pooling  # noqa: E402
from alea.reference import load_who_benin, mu_lookup  # noqa: E402
from alea.synth import InsurerSpec, simulate, true_mu  # noqa: E402

MARKET = [  # (clé, contrats, multiplicateur, shape_tilt)
    ("A", 40_000, 0.95, 0.0), ("B", 15_000, 1.05, 0.0), ("C", 8_000, 0.90, 0.30),
    ("D", 5_000, 1.10, -0.25), ("E", 2_500, 1.20, 0.0), ("F", 1_500, 1.00, 0.40),
]
METHODS = ["Table OMS seule", "Expérience propre seule", "Table de marché",
           "Aléa (crédibilité globale)", "Aléa (bandes d'âge)", "Aléa (bandes, marché sans soi)"]


def one_market(rep: int, ref) -> list[dict]:
    specs = [InsurerSpec(k, k, n, m, 0.55, "alpha", 1000 * rep + i, shape_tilt=t)
             for i, (k, n, m, t) in enumerate(MARKET)]
    cells, truth = {}, {}
    for s in specs:
        cells[s.key] = experience.exposures(simulate(s))
        truth[s.key] = true_mu(s)
    aggs = [pooling.shareable_aggregates(c, k)[0] for k, c in cells.items()]
    mkt = pipeline.market_model(aggs)
    shared = {a["assureur"].iloc[0]: a.drop(columns="assureur") for a in aggs}
    rows = []
    for s in specs:
        own = experience.fit_relative_glm(cells[s.key], ref)
        own_mu = experience.to_mu_lookup(own["table"], ref)
        cred = pipeline.credibility_for(shared, s.key, mkt["mu"])
        cred_loo = pipeline.credibility_loo(shared, s.key)
        tables = dict(zip(METHODS, [ref, own_mu, mkt["mu"], cred["mu"], cred["mu_bands"], cred_loo["mu_bands"]]))
        for name, mu in tables.items():
            rows.append({"rep": rep, "assureur": s.key, "contrats": s.n_policies, "décès": own["deaths"],
                         "méthode": name, "erreur": pipeline.weighted_log_error(mu, truth[s.key], mkt["cells"]),
                         "Z_M": float(cred["theta"].set_index("sex").loc["M", "Z"]), "K": cred["K"]["K"]})
    return rows


def main(R: int):
    t0 = time.time()
    ref = mu_lookup(load_who_benin())
    rows = []
    for rep in range(R):
        rows += one_market(rep, ref)
        print(f"marché {rep + 1}/{R} — {time.time() - t0:.0f} s", flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "montecarlo_raw.csv", index=False)
    piv = df.pivot_table(index=["assureur", "contrats"], columns="méthode", values="erreur", aggfunc="mean")[METHODS]
    meta = df[df["méthode"] == METHODS[0]].groupby(["assureur", "contrats"]).agg(décès=("décès", "mean"), Z=("Z_M", "mean"))
    best = df.loc[df.groupby(["rep", "assureur"])["erreur"].idxmin()].groupby("assureur")["méthode"].value_counts().unstack(fill_value=0)
    L = ["# Évaluation Monte-Carlo", "",
         f"{R} marchés simulés de 6 assureurs fictifs (données propres). Erreur logarithmique absolue moyenne "
         "par rapport à la vraie mortalité, pondérée par l'exposition, âges 25 à 70 ans. Plus bas = mieux.", "",
         "| Assureur | Contrats | Décès moyens | Crédibilité Z (hommes) | " + " | ".join(METHODS) + " |",
         "|---|---|---|---|" + "---|" * len(METHODS)]
    for (k, n), r in piv.iterrows():
        mt = meta.loc[(k, n)]
        L.append(f"| {k} | {n:,} | {mt['décès']:.0f} | {mt['Z']:.0%} | ".replace(",", " ") +
                 " | ".join(f"{r[m]:.1%}" for m in METHODS) + " |")
    best_md = ["| Assureur | " + " | ".join(best.columns) + " |", "|---|" + "---|" * len(best.columns)]
    best_md += [f"| {k} | " + " | ".join(str(v) for v in r) + " |" for k, r in best.iterrows()]
    L += ["", "## Nombre de marchés où chaque méthode est la meilleure", "", *best_md,
          "", f"Durée : {time.time() - t0:.0f} s."]
    (out / "montecarlo.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
