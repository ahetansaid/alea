"""Faits calculés et formatés, seule matière autorisée pour la rédaction de la note."""
from __future__ import annotations

from .experience import OBS_END, OBS_START
from .report import fmt_num, fmt_pct


def _band_text(tb, sex: str, col: str, two: bool = False) -> str:
    t = tb[tb["sex"] == sex]
    if two:
        return " ; ".join(f"{b} : {fmt_pct(lo)} à {fmt_pct(hi)}"
                          for b, lo, hi in zip(t["band"].astype(str), t["theta_lo"], t["theta_hi"]))
    return " ; ".join(f"{b} : {fmt_pct(v)}" for b, v in zip(t["band"].astype(str), t[col]))


def build(name: str, summary: dict, own_fit: dict, cred: dict, n_insurers: int, pricing_case: dict,
          mode: str = "global") -> dict:
    th = cred["theta"].set_index("sex")

    def f(label, text):
        return {"libellé": label, "texte": text}

    pr, pref = pricing_case["prime_retenue"], pricing_case["prime_ref"]
    if mode in ("bandes", "loo"):
        tb = cred["theta_bands"]
        z_m, z_f = _band_text(tb, "M", "Z"), _band_text(tb, "F", "Z")
        th_m, th_f = _band_text(tb, "M", "theta_retenu"), _band_text(tb, "F", "theta_retenu")
        ic_m, ic_f = _band_text(tb, "M", None, two=True), _band_text(tb, "F", None, two=True)
        modele = ("par bandes d'âge, marché ajusté sans l'assureur évalué (leave-one-out)" if mode == "loo"
                  else "par bandes d'âge, avec repli sur le niveau global quand la bande compte moins de 20 décès attendus")
    else:
        z_m, z_f = fmt_pct(th.loc["M", "Z"]), fmt_pct(th.loc["F", "Z"])
        th_m, th_f = fmt_pct(th.loc["M", "theta"]), fmt_pct(th.loc["F", "theta"])
        ic_m = f"{fmt_pct(th.loc['M', 'theta_lo'])} à {fmt_pct(th.loc['M', 'theta_hi'])}"
        ic_f = f"{fmt_pct(th.loc['F', 'theta_lo'])} à {fmt_pct(th.loc['F', 'theta_hi'])}"
        modele = "global (un facteur par sexe)"
    F = {
        "assureur": f("Portefeuille", name),
        "periode": f("Période d'observation", f"{OBS_START.year} à {OBS_END.year - 1}"),
        "lignes_initiales": f("Lignes du fichier", fmt_num(summary["lignes initiales"])),
        "lignes_exclues": f("Lignes exclues après contrôle", fmt_num(summary["exclues"])),
        "capitaux_corriges": f("Capitaux corrigés", fmt_num(summary["capitaux corrigés"])),
        "exposition": f("Exposition (années-personnes)", fmt_num(own_fit["exposure"])),
        "deces": f("Décès observés", fmt_num(own_fit["deaths"])),
        "ae_ref": f("Décès observés / attendus selon la table OMS", fmt_pct(own_fit["ae_ref"])),
        "n_assureurs": f("Assureurs mutualisés", fmt_num(n_insurers)),
        "modele": f("Modèle de crédibilité", modele),
        "Z_M": f("Crédibilité hommes", z_m),
        "Z_F": f("Crédibilité femmes", z_f),
        "theta_M": f("Mortalité retenue hommes, en % de la table de marché", th_m),
        "theta_F": f("Mortalité retenue femmes, en % de la table de marché", th_f),
        "theta_M_ic": f("Intervalle crédible à 95 % hommes", ic_m),
        "theta_F_ic": f("Intervalle crédible à 95 % femmes", ic_f),
        "tarif_cas": f("Cas de tarification", pricing_case["libelle"]),
        "prime_retenue": f("Prime annuelle pure, table retenue", f"{fmt_num(pr)} FCFA"),
        "prime_ref": f("Prime annuelle pure, table de population OMS", f"{fmt_num(pref)} FCFA"),
        "ecart_prime": f("Écart de prime", fmt_pct(pr / pref - 1)),
    }
    pic = pricing_case.get("prime_ic")
    if pic:
        F["prime_ic"] = f("Intervalle de bootstrap à 95 % sur la prime", f"{fmt_num(pic[0])} à {fmt_num(pic[1])} FCFA")
    return F
