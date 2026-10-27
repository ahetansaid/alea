# -*- coding: utf-8 -*-
"""Monte-Carlo adversarial : où Aléa casse-t-il ?

Quatre scénarios hostiles pour éprouver le pipeline au-delà du cas nominal :
  S1 marché minimal (2 assureurs) ; S2 formes extrêmes (tilts jusqu'à ±0,8) ;
  S3 tout petit portefeuille (< 1 500 contrats pour tous) ; S4 marché dominé
  (un assureur porte 80 % de l'exposition).
Produit reports/stress.md. Usage : python scripts/stress_mc.py [R]
"""
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

SCENARIOS = {
    "S1 marché à 2 assureurs": [("A", 5_000, 1.0, 0.0), ("B", 1_000, 1.0, 0.30)],
    "S2 formes extrêmes": [("A", 20_000, 1.0, 0.0), ("B", 10_000, 1.0, 0.80), ("C", 8_000, 1.0, -0.80),
                           ("D", 4_000, 1.0, 0.45), ("E", 2_000, 1.0, -0.45), ("F", 1_500, 1.0, 0.0)],
    "S3 très petits porteurs": [("A", 1_200, 1.0, 0.0), ("B", 900, 1.05, 0.20), ("C", 700, 0.95, -0.20),
                                ("D", 500, 1.0, 0.35), ("E", 400, 1.1, 0.0)],
    "S4 marché dominé": [("Dom", 60_000, 1.0, 0.50), ("b1", 3_000, 1.0, 0.0), ("b2", 2_000, 1.0, 0.0),
                         ("b3", 1_500, 1.0, 0.10), ("b4", 1_000, 1.0, 0.0)],
}
METHODS = ["Table OMS seule", "Expérience propre", "Table de marché", "Aléa global", "Aléa bandes", "Aléa LOO"]


def one_market(scen: str, config, rep: int, si: int, ref) -> list[dict]:
    specs = [InsurerSpec(k, k, n, m, 0.55, "alpha", 777 * si + 1000 * rep + i, shape_tilt=t)
             for i, (k, n, m, t) in enumerate(config)]
    cells, truth = {}, {}
    for s in specs:
        cells[s.key] = experience.exposures(simulate(s))
        truth[s.key] = true_mu(s)
    aggs = [pooling.shareable_aggregates(c, k)[0] for k, c in cells.items()]
    shared = {k: a.drop(columns="assureur") for k, a in zip(cells, aggs)}
    try:
        mkt = pipeline.market_model(aggs)
    except ValueError as exc:
        return [{"scénario": scen, "rep": rep, "assureur": "*", "méthode": "GARDE-FOU", "erreur": np.nan,
                 "drapeau": str(exc)[:80], "repli": np.nan}]
    rows = []
    for s in specs:
        own = experience.fit_relative_glm(cells[s.key], ref)
        own_mu = experience.to_mu_lookup(own["table"], ref)
        cred = pipeline.credibility_for(shared, s.key, mkt["mu"])
        tables = {"Table OMS seule": ref, "Expérience propre": own_mu, "Table de marché": mkt["mu"],
                  "Aléa global": cred["mu"], "Aléa bandes": cred["mu_bands"]}
        try:
            tables["Aléa LOO"] = pipeline.credibility_loo(shared, s.key)["mu_bands"]
            drapeau = ""
        except ValueError as exc:
            drapeau = "LOO degenere: " + str(exc)[:40]
        n_repli = int(cred["theta_bands"]["repli"].sum()) if len(cred["theta_bands"]) else 0
        for name, mu in tables.items():
            err = pipeline.weighted_log_error(mu, truth[s.key], mkt["cells"])
            rows.append({"scénario": scen, "rep": rep, "assureur": s.key, "méthode": name, "erreur": err,
                         "drapeau": drapeau if name == "Aléa LOO" else "", "repli": n_repli,
                         "décès": own["deaths"]})
    return rows


def main(R: int):
    t0 = time.time()
    ref = mu_lookup(load_who_benin())
    rows = []
    for si, (scen, config) in enumerate(SCENARIOS.items()):
        for rep in range(R):
            rows += one_market(scen, config, rep, si, ref)
            print(f"{scen} — marché {rep + 1}/{R} — {time.time() - t0:.0f} s", flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "stress_raw.csv", index=False)

    L = ["# Monte-Carlo adversarial : où Aléa casse", "",
         f"{R} marchés par scénario. Erreur logarithmique absolue moyenne (pondérée exposition, 25-70 ans), "
         "hors cellules où la méthode est indisponible. Plus bas = mieux.", ""]
    piv = (df[df["méthode"] != "GARDE-FOU"].pivot_table(index=["scénario", "assureur"], columns="méthode",
             values="erreur", aggfunc="mean").reindex(columns=METHODS))
    deces = df[df["méthode"] == "Table OMS seule"].groupby(["scénario", "assureur"])["décès"].mean()
    repli = df[df["méthode"] == "Table OMS seule"].groupby(["scénario", "assureur"])["repli"].mean()
    L += ["", "| Scénario | Assureur | Décès moy. | Bandes en repli | " + " | ".join(METHODS) + " |",
          "|---|---|---|---|" + "---|" * len(METHODS)]
    for (scen, k), r in piv.iterrows():
        cells = " | ".join("n/a" if pd.isna(r[m]) else f"{r[m]:.1%}" for m in METHODS)
        L.append(f"| {scen} | {k} | {deces.loc[(scen, k)]:.0f} | {repli.loc[(scen, k)]:.1f} | {cells} |")
    guards = df[df["méthode"] == "GARDE-FOU"]
    loo_fail = df[df["drapeau"].astype(str).str.startswith("LOO")]
    worst = []
    for (scen, k), r in piv.iterrows():
        if pd.isna(r["Aléa bandes"]):
            continue
        best_other = np.nanmin([r["Table OMS seule"], r["Expérience propre"], r["Table de marché"]])
        if r["Aléa bandes"] > best_other * 1.25:
            worst.append((scen, k, r["Aléa bandes"], best_other))
    L += ["", "## Incidents", "",
          f"- Gardes-fous déclenchés sur un marché complet : {len(guards)}. "
          f"- Leave-one-out dégénéré : {len(loo_fail)} tirages (assureur).",
          "- Là où Aléa (bandes) perd de plus de 25 % face à la meilleure autre méthode :"]
    if worst:
        for scen, k, a, b in worst:
            L.append(f"  - {scen} / {k} : {a:.1%} contre {b:.1%} pour la meilleure alternative")
    else:
        L.append("  - aucun")
    L += ["", f"Durée : {time.time() - t0:.0f} s."]
    (out / "stress.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
