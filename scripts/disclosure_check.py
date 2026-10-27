"""Audit de confidentialité de la mutualisation : où sont les fuites potentielles ?

Produit reports/disclosure.md. Trois contrôles :
1. Attaque par totaux auxiliaires : le bilan de partage publié par assureur (cellules et décès
   supprimés) permet-il de reconstituer une cellule individuelle ?
2. Cellules à contributeur unique : un total de marché à un seul contributeur est une donnée
   individuelle déguisée en agrégat.
3. Cellules à un seul décès avant/après masquage.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alea import pipeline, pooling  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
OUT = ROOT / "reports"
KEYS = ("alpha", "beta", "gamma", "delta")


def main():
    OUT.mkdir(exist_ok=True)
    raw_cells, aggs, supp = {}, [], []
    for k in KEYS:
        r = pipeline.auto_run(SAMPLES / f"portefeuille_{k}.csv", k)
        raw_cells[k] = r["cells"]
        a, info = pooling.shareable_aggregates(r["cells"], k)
        aggs.append(a)
        supp.append(info)

    allc = pd.concat(aggs, ignore_index=True)

    # 1. totaux auxiliaires : le total supprimé d'un assureur identifie une cellule individuelle
    #    seulement s'il n'a exactement qu'une cellule supprimée.
    sole = [s for s in supp if s["cellules supprimées"] == 1]
    n_suppr = sum(s["cellules supprimées"] for s in supp)

    # 2. cellules à contributeur unique, puis masquage
    n_contrib = allc.groupby(["sex", "age"])["assureur"].nunique()
    single = n_contrib[n_contrib < 2]
    masked, mi = pooling.mask_single_contributor(aggs)
    after = pd.concat(masked, ignore_index=True)
    after_contrib = after.groupby(["sex", "age"])["assureur"].nunique()
    bad = int((after_contrib < 2).sum())

    # 3. cellules à un seul décès
    one_before = int((allc["D"] == 1).sum())
    one_after = int((after["D"] == 1).sum())

    # 4. attaque par double seuil : si deux tables de marché sont publiées avec des seuils
    #    différents (glissade du curseur), la soustraction des deux peut reconstituer la
    #    cellule exacte d'un assureur qui disparaît quand on relève le seuil.
    t1, t2 = pooling.MIN_EXPOSURE, 60.0

    def market_at(t):
        ag = [pooling.shareable_aggregates(c, k, min_exposure=t)[0] for k, c in raw_cells.items()]
        mk, _ = pooling.mask_single_contributor(ag)
        cat = pd.concat(mk, ignore_index=True)
        m = pooling.market(mk)
        totals = {(s, a): (E, D) for s, a, E, D in zip(m["sex"], m["age"], m["E"], m["D"])}
        contribs = cat.groupby(["sex", "age"])["assureur"].apply(set).to_dict() if len(cat) else {}
        return totals, contribs, ag

    tot1, con1, ag1 = market_at(t1)
    tot2, _con2, _ag2 = market_at(t2)
    leaks = []
    for agg in ag1:
        ins = agg["assureur"].iloc[0] if len(agg) else None
        for row in agg[agg["E"] < t2].itertuples():
            key = (row.sex, row.age)
            if key in tot1 and key in tot2 and ins in con1.get(key, set()):
                if abs(tot1[key][0] - tot2[key][0] - row.E) < 1e-9 and tot1[key][1] - tot2[key][1] == row.D:
                    leaks.append((ins, key[0], key[1], row.E, row.D))

    L = ["# Audit de confidentialité de la mutualisation", "",
         "Contrôle sur les quatre portefeuilles fictifs de démonstration, seuil d'exposition minimale de "
         f"{pooling.MIN_EXPOSURE} années-personnes par cellule partagée.", "",
         "## 1. Petites cellules supprimées avant partage", "",
         "| Assureur | Cellules partagées | Cellules supprimées | Exposition supprimée (années) | Décès supprimés |",
         "|---|---|---|---|---|"]
    for s in supp:
        L.append(f"| {s['assureur']} | {s['cellules partagées']} | {s['cellules supprimées']} | "
                 f"{s['exposition supprimée (années)']} | {s['décès supprimés']} |")
    L += ["", f"**{n_suppr}** cellules supprimées au total par le seuil. Elles ne sont envoyées à personne : "
          "le total de marché ne les contient pas, la soustraction des autres contributeurs ne reconstitue "
          "donc rien.", "",
          "Le seul levier restant est le **total auxiliaire** publié au bilan de partage (exposition et décès "
          "supprimés par assureur) : il identifie une cellule individuelle si un assureur n'a exactement "
          f"**qu'une** cellule supprimée. Cas observé : {len(sole)} assureur(s). "
          "Tant que chaque assureur a plusieurs cellules supprimées, le total auxiliaire ne localize aucune "
          "cellule. Une gouvernance prudente publiera ces totaux par tranches plutôt que bruts.", "",
          "## 2. Cellules à contributeur unique (le vrai risque)", "",
          f"Sur {allc.groupby(['sex', 'age']).ngroups} cellules (sexe, âge) partagées par au moins un assureur, "
          f"**{len(single)}** n'ont qu'un seul contributeur. Pour elles, le total de marché publié à tous est "
          "exactement la donnée individuelle de cet assureur : c'est le vecteur de fuite réel, et le seuil "
          "d'exposition ne le couvre pas (une cellule à contributeur unique peut être volumineuse).", "",
          "Masquage appliqué par Aléa (`pooling.mask_single_contributor`, appelé systématiquement par "
          f"`pipeline.market_model`) : {mi['cellules_a_contributeur_unique']} cellules retirées du marché pour "
          f"tous, soit {mi['expositions_supprimees (annees)']} années d'exposition et {mi['deces_supprimes']} décès. "
          f"Après masquage, il reste {bad} cellule(s) publiée(s) à contributeur unique (contrôle : doit être 0).", "",
          "## 3. Cellules à un seul décès", "",
          f"- Avant masquage : {one_before} paires (assureur, cellule) avec D = 1.",
          f"- Après masquage des cellules à contributeur unique : {one_after}.", "",
          "## 4. Attaque par double seuil (la glissade du curseur)", "",
          f"Deux tables de marché publiées avec des seuils différents ({t1:.0f} puis {t2:.0f} années) donnent "
          "à soustraire : toute cellule d'un assureur partagée au premier seuil et retirée au second réapparaît "
          f"exactement dans la différence. Cellules ainsi reconstituées : **{len(leaks)}**.", ""]
    if leaks:
        L += ["| Assureur | Sexe | Âge | Exposition reconstituée | Décès reconstitués |", "|---|---|---|---|---|"]
        L += [f"| {ins} | {s} | {a} | {e:.1f} | {d} |" for ins, s, a, e, d in leaks[:20]]
        if len(leaks) > 20:
            L.append(f"… et {len(leaks) - 20} autres.")
        L += ["", "**Règle de gouvernance : le seuil d'exposition minimale est une constante du marché, pas "
              "une préférence de session.** Il doit être identique chez tous les contributeurs et ne jamais "
              "varier ; sinon l'historique des publications devient un jeu de soustractions."]
    L += ["",
          "Un décès isolé dans une cellule à deux contributeurs ou plus reste une valeur individuelle dans un "
          "total, mais sans information auxiliaire (qui habite où), la réidentification n'est pas mécanique. "
          "Le relevé par cellule reste malgré tout sensible : le partager en comité n'est pas le publier.", "",
          "## Conclusion", "",
          "- Le seuil d'exposition minimale protège contre les petites cellules ; il ne protège pas contre les "
          "cellules à contributeur unique.",
          "- Aléa masque désormais systématiquement ces cellules avant mutualisation.",
          "- L'interface verrouille le seuil de partage à la constante du marché : le curseur ne fait que "
          "simuler localement l'effet du seuil sur le portefeuille, la table de marché n'est jamais publiée "
          "à un autre seuil.",
          "- Publier le nombre de contributeurs par cellule, et trancher les totaux auxiliaires supprimés."]
    text = "\n".join(L)
    (OUT / "disclosure.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
