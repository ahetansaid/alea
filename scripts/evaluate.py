"""Évaluation de bout en bout sur les portefeuilles fictifs, contre la vérité connue.

Produit reports/evaluation.md et reports/evaluation.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alea import experience, pipeline, pooling, pricing, quality  # noqa: E402
from alea.reference import load_who_benin, mu_lookup  # noqa: E402
from alea.synth import COLUMNS, INSURERS  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
OUT = ROOT / "reports"
CANON = ["policy_id", "birth_date", "sex", "entry_date", "exit_date", "exit_reason", "sum_assured", "product"]


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    ref = mu_lookup(load_who_benin())
    runs, res = {}, {"mapping": {}, "quality": {}, "credibility": {}, "pricing": {}}
    for spec in INSURERS:
        r = pipeline.auto_run(SAMPLES / f"portefeuille_{spec.key}.csv", spec.key)
        runs[spec.key] = r
        expected = dict(zip(CANON, COLUMNS[spec.style]))
        got = dict(zip(r["mapping"]["champ"], r["mapping"]["colonne source"]))
        res["mapping"][spec.key] = {"correctes": sum(got.get(k) == v for k, v in expected.items()), "total": len(CANON),
                                    "moteur": r["engine"]}
        truth = pd.read_csv(SAMPLES / f"verite_erreurs_{spec.key}.csv")
        res["quality"][spec.key] = quality.evaluate(r["issues"], truth, r["canon"]).to_dict("records")

    aggs, supp = [], []
    for k, r in runs.items():
        a, info = pooling.shareable_aggregates(r["cells"], k)
        aggs.append(a)
        supp.append(info)
    res["suppression"] = supp
    mkt = pipeline.market_model(aggs)
    shared = {k: a.drop(columns="assureur") for k, a in zip(runs, aggs)}
    weights = mkt["cells"]
    for spec in INSURERS:
        tm = pd.read_csv(SAMPLES / f"verite_mortalite_{spec.key}.csv")
        truth_mu = {"M": tm["mu_M"].to_numpy(), "F": tm["mu_F"].to_numpy()}
        own = experience.fit_relative_glm(runs[spec.key]["cells"], ref)
        own_mu = experience.to_mu_lookup(own["table"], ref)
        cred = pipeline.credibility_for(shared, spec.key, mkt["mu"])
        cred_loo = pipeline.credibility_loo(shared, spec.key)
        err = {name: pipeline.weighted_log_error(mu, truth_mu, weights) for name, mu in
               {"table OMS (population)": ref, "expérience propre seule (GLM)": own_mu,
                "table de marché": mkt["mu"], "Aléa : crédibilité globale": cred["mu"],
                "Aléa : crédibilité par bandes": cred["mu_bands"],
                "Aléa : bandes, marché sans soi": cred_loo["mu_bands"]}.items()}
        th = cred["theta"].set_index("sex")
        res["credibility"][spec.key] = {
            "décès observés": int(own["deaths"]), "K": round(cred["K"]["K"], 1),
            "tau2_bandes": round(cred["K_bands"]["tau2_global"], 4),
            "Z_M": round(float(th.loc["M", "Z"]), 3), "Z_F": round(float(th.loc["F", "Z"]), 3),
            "theta_M": round(float(th.loc["M", "theta"]), 3), "theta_F": round(float(th.loc["F", "theta"]), 3),
            "erreur_log_moyenne": {k: round(v, 4) for k, v in err.items()}}
        rows = pricing.compare({"OMS population": ref, "vérité (inconnue en pratique)": truth_mu,
                                "Aléa (global)": cred["mu"], "Aléa (bandes)": cred["mu_bands"]},
                               "M", 40, 10, 5_000_000, 0.035)
        res["pricing"][spec.key] = rows

    res["durée_s"] = round(time.time() - t0, 1)
    (OUT / "evaluation.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(res)
    print(json.dumps(res["credibility"], ensure_ascii=False, indent=1))
    print("mapping", res["mapping"])
    print(f"terminé en {res['durée_s']} s")


def write_md(res):
    L = ["# Évaluation d'Aléa sur portefeuilles fictifs", "",
         "Données entièrement synthétiques, générées à partir de la table OMS du Bénin (2023) avec une vérité connue.",
         "Les chiffres ci-dessous mesurent ce que le prototype retrouve, pas une performance sur données réelles.", ""]
    L += ["## 1. Correspondance des colonnes", "", "| Assureur | Champs correctement reconnus | Moteur |", "|---|---|---|"]
    for k, v in res["mapping"].items():
        L.append(f"| {k} | {v['correctes']} / {v['total']} | {v['moteur']} |")
    L += ["", "## 2. Détection des erreurs injectées", ""]
    for k, rows in res["quality"].items():
        L += [f"### {k}", "", "| Type | Injectées | Signalées | Précision | Rappel |", "|---|---|---|---|---|"]
        for r in rows:
            kind = r["type d'erreur"]
            L.append(f"| {kind} | {r['injectées']} | {r['signalées']} | {r['précision']} | {r['rappel']} |")
        L.append("")
    L += ["Note : l'assureur Gamma exporte ses dates avec des années à deux chiffres. Une naissance décalée de "
          "100 ans (erreur « impossible_age ») y devient indiscernable d'une date correcte : l'erreur injectée "
          "n'est pas représentable dans ce format, d'où un rappel nul sur ce type pour Gamma.", ""]
    L += ["## 3. Mutualisation : cellules supprimées avant partage", "", "| Assureur | Partagées | Supprimées | Exposition supprimée |", "|---|---|---|---|"]
    for s in res["suppression"]:
        L.append(f"| {s['assureur']} | {s['cellules partagées']} | {s['cellules supprimées']} | {s['exposition supprimée (années)']} |")
    L += ["", "## 4. Erreur des tables estimées par rapport à la vérité",
          "", "Erreur logarithmique absolue moyenne, pondérée par l'exposition, âges 25 à 70 ans (plus bas = mieux).", ""]
    names = list(next(iter(res["credibility"].values()))["erreur_log_moyenne"])
    L += ["| Assureur | Décès | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for k, v in res["credibility"].items():
        L.append(f"| {k} | {v['décès observés']} | " + " | ".join(str(v["erreur_log_moyenne"][n]) for n in names) + " |")
    L += ["", "## 5. Prime annuelle pure — temporaire décès, homme 40 ans, 10 ans, 5 000 000 FCFA, taux 3,5 %", ""]
    for k, rows in res["pricing"].items():
        L.append(f"- **{k}** : " + " ; ".join(f"{r['table']} = {r['prime_annuelle']:,} FCFA".replace(",", " ") for r in rows))
    L += ["", f"Durée totale : {res['durée_s']} s."]
    (OUT / "evaluation.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
