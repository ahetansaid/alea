"""Aléa — interface de démonstration (Streamlit).

Lancer : streamlit run app.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from alea import audit, bootstrap, credibility, experience, facts, mapping, normalize, pipeline, pooling, pricing, quality, report
from alea.reference import load_regulatory, load_who_benin, mu_lookup
from alea.synth import INSURERS

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "data" / "samples"
NAMES = {s.key: s.name for s in INSURERS}

st.set_page_config(page_title="Aléa — actuariat augmenté", page_icon="📈", layout="wide")
S = st.session_state

STEPS = ["1. Données", "2. Colonnes", "3. Qualité", "4. Expérience", "5. Mutualisation", "6. Tarification", "7. Note technique"]
with st.sidebar:
    st.title("Aléa")
    st.caption("Actuariat augmenté — l'IA prépare, l'actuaire décide.")
    step = st.radio("Étapes", STEPS, label_visibility="collapsed")
    st.divider()
    st.caption("Prototype sur données **fictives**. Aucune donnée réelle n'est utilisée.")
    show_truth = st.toggle("Afficher la vérité (démo)", value=False,
                           help="Les portefeuilles fictifs ont une mortalité connue : utile pour juger la qualité des estimations.")


@st.cache_resource
def ref_tables():
    who = load_who_benin()
    return mu_lookup(who), load_regulatory()


@st.cache_data(show_spinner="Correspondance des colonnes (modèle d'embeddings)…")
def cached_mapping(raw: pd.DataFrame):
    return mapping.propose_mapping(raw)


@st.cache_data(show_spinner="Les autres assureurs exécutent Aléa chez eux…")
def other_insurers(exclude: str) -> dict:
    out = {}
    for k in NAMES:
        if k == exclude:
            continue
        r = pipeline.auto_run(SAMPLES / f"portefeuille_{k}.csv", k)
        out[k] = r["cells"]
    return out


def need(*keys):
    missing = [k for k in keys if k not in S]
    if missing:
        st.info("Terminez d'abord l'étape précédente.")
        st.stop()


REF_MU, CIMA = ref_tables()

# ------------------------------------------------------------------ 1. Données
if step == STEPS[0]:
    st.header("1. Données du portefeuille")
    st.write("Fichier brut d'un assureur, tel qu'exporté de son système : colonnes, formats et codes propres à chacun.")
    src = st.radio("Source", ["Portefeuille fictif fourni", "Importer un fichier CSV"], horizontal=True)
    if src.startswith("Portefeuille"):
        key = st.selectbox("Assureur", list(NAMES), format_func=NAMES.get, index=2)
        data = (SAMPLES / f"portefeuille_{key}.csv").read_bytes()
        name = NAMES[key]
    else:
        up = st.file_uploader("Fichier CSV", type=["csv", "txt"])
        if not up:
            st.stop()
        data, key, name = up.getvalue(), "import", up.name
    if st.button("Charger", type="primary"):
        for k in list(S.keys()):
            del S[k]
        S.raw = pipeline.read_portfolio(data)
        S.key, S.name, S.sha = key, name, audit.sha256(data)
    if "raw" in S:
        st.success(f"{S.name} : {len(S.raw):,} lignes, {S.raw.shape[1]} colonnes".replace(",", " "))
        st.dataframe(S.raw.head(15), use_container_width=True)

# ------------------------------------------------------------------ 2. Colonnes
elif step == STEPS[1]:
    need("raw")
    st.header("2. Correspondance des colonnes")
    m, engine = cached_mapping(S.raw)
    st.caption(f"Moteur sémantique : {engine}. Confiance = sens de l'en-tête + profil des valeurs.")
    edited = st.data_editor(
        m, use_container_width=True, hide_index=True, disabled=["champ", "libellé", "confiance", "sémantique", "profil", "à confirmer"],
        column_config={"colonne source": st.column_config.SelectboxColumn(options=list(S.raw.columns), required=True),
                       "confiance": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    if edited["à confirmer"].any():
        st.warning("Certaines correspondances sont à confirmer : vérifiez-les avant de valider.")
    if st.button("Valider la correspondance", type="primary"):
        mp = dict(zip(edited["champ"], edited["colonne source"]))
        if len(set(mp.values())) < len(mp):
            st.error("Une même colonne source est affectée à deux champs.")
            st.stop()
        S.mapping = mp
        S.canon, S.norm_log = normalize.normalize(S.raw, mp)
        S.pop("issues", None)
        st.success("Correspondance validée. Données mises au format standard.")
    if "norm_log" in S:
        st.subheader("Journal de normalisation")
        st.dataframe(pd.DataFrame(S.norm_log), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ 3. Qualité
elif step == STEPS[2]:
    need("canon")
    st.header("3. Contrôle qualité")
    st.write("Contrôles de règles et détection d'anomalies (Isolation Forest). **Chaque action est soumise à votre décision.**")
    if "issues" not in S:
        S.issues = quality.detect(S.canon)
    iss = S.issues
    c1, c2, c3 = st.columns(3)
    c1.metric("Lignes", f"{len(S.canon):,}".replace(",", " "))
    c2.metric("Anomalies signalées", f"{(iss['contrôle'] != 'atypical_profile').sum():,}".replace(",", " "))
    c3.metric("Profils atypiques à examiner", int((iss["contrôle"] == "atypical_profile").sum()))
    st.dataframe(iss.groupby(["contrôle", "description", "action proposée"]).size().rename("lignes").reset_index(),
                 use_container_width=True, hide_index=True)
    edited = st.data_editor(iss, use_container_width=True, hide_index=True, height=320,
                            disabled=[c for c in iss.columns if c != "accepter"])
    if S.key in NAMES and show_truth:
        truth = pd.read_csv(SAMPLES / f"verite_erreurs_{S.key}.csv")
        st.subheader("Vérification contre les erreurs injectées (démo)")
        st.dataframe(quality.evaluate(edited, truth, S.canon), use_container_width=True, hide_index=True)
    if st.button("Appliquer les décisions", type="primary"):
        S.issues = edited
        S.clean, S.q_summary = quality.apply(S.canon, edited)
        S.cells = experience.exposures(S.clean)
        S.decisions = edited.groupby(["contrôle", "accepter"]).size().rename("n").reset_index().to_dict("records")
        st.success("Décisions appliquées.")
    if "q_summary" in S:
        st.json(S.q_summary)

# ------------------------------------------------------------------ 4. Expérience
elif step == STEPS[3]:
    need("cells")
    st.header("4. Étude d'expérience")
    fit = experience.fit_relative_glm(S.cells, REF_MU)
    S.own_fit = fit
    c1, c2, c3 = st.columns(3)
    c1.metric("Exposition (années-personnes)", f"{fit['exposure']:,.0f}".replace(",", " "))
    c2.metric("Décès observés", f"{fit['deaths']:.0f}")
    c3.metric("Observés / attendus (table OMS)", f"{fit['ae_ref']:.0%}")
    sex = st.radio("Sexe", ["M", "F"], horizontal=True, format_func={"M": "Hommes", "F": "Femmes"}.get)
    t = fit["table"][fit["table"]["sex"] == sex]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t["age"], y=t["mu_hi"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=t["age"], y=t["mu_lo"], fill="tonexty", line=dict(width=0), name="IC 95 %", fillcolor="rgba(31,78,121,0.2)"))
    fig.add_trace(go.Scatter(x=t["age"], y=t["mu"], name="GLM (expérience propre)", line=dict(color="#1f4e79", width=3)))
    fig.add_trace(go.Scatter(x=t["age"], y=t["crude"], mode="markers", name="Taux bruts", marker=dict(color="#888", size=5)))
    fig.add_trace(go.Scatter(x=t["age"], y=t["mu_ref"], name="Table OMS Bénin (population)", line=dict(color="#e69500", dash="dash")))
    if show_truth and S.key in NAMES:
        tm = pd.read_csv(SAMPLES / f"verite_mortalite_{S.key}.csv")
        tm = tm[tm["age"].between(20, 80)]
        fig.add_trace(go.Scatter(x=tm["age"], y=tm[f"mu_{sex}"], name="Vérité (démo)", line=dict(color="green", dash="dot")))
    fig.update_layout(yaxis_type="log", yaxis_title="Force de mortalité (échelle log)", xaxis_title="Âge", height=480)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("GLM de Poisson relatif à la table OMS : log E[D] = log(E·μ_ref) + polynôme de l'âge + effet sexe.")

# ------------------------------------------------------------------ 5. Mutualisation
elif step == STEPS[4]:
    need("cells")
    st.header("5. Mutualisation de marché et crédibilité")
    st.write("Chaque assureur ne partage que des **agrégats** (exposition et décès par sexe et âge). "
             "Les petites cellules sont supprimées avant partage, et les cellules où un seul assureur "
             "contribue sont retirées du marché : aucune donnée personnelle ne circule.")
    st.caption(f"Le seuil de partage est une **constante du marché** ({int(pooling.MIN_EXPOSURE)} années) : le "
               "publier à deux seuils différents permettrait de reconstituer par soustraction les cellules "
               "individuelles (40 cellules reconstituables sur le jeu de démonstration, voir "
               "reports/disclosure.md). Le curseur ci-dessous est une **simulation locale**, votre table de "
               "marché n'est jamais recalculée à un autre seuil.")
    min_e = st.slider("Seuil simulé pour votre propre portefeuille (années)", 0, 100, int(pooling.MIN_EXPOSURE), 5)
    others = other_insurers(S.key)
    aggs, infos = [], []
    own_agg, own_info = pooling.shareable_aggregates(S.cells, S.key, min_e)
    aggs.append(pooling.shareable_aggregates(S.cells, S.key)[0]); infos.append(own_info)
    for k, cells in others.items():
        a, info = pooling.shareable_aggregates(cells, k)
        aggs.append(a); infos.append(info)
    st.dataframe(pd.DataFrame(infos), use_container_width=True, hide_index=True)
    with st.expander("Ce qui est réellement partagé (extrait)"):
        st.dataframe(own_agg.head(20), use_container_width=True, hide_index=True)
    try:
        mkt = pipeline.market_model(aggs)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    mi = mkt["mask_info"]
    if mi and mi["cellules_a_contributeur_unique"]:
        st.warning(f"Confidentialité : {mi['cellules_a_contributeur_unique']} cellule(s) (sexe, âge) ne comptent "
                   f"qu'un seul contributeur ({mi['deces_supprimes']} décès, "
                   f"{mi['expositions_supprimees (annees)']} années d'exposition). Elles sont retirées du marché "
                   "pour tous, car un agrégat à contributeur unique est une donnée individuelle déguisée.")
    else:
        st.caption("Aucune cellule à contributeur unique : chaque cellule du marché agrège au moins deux assureurs.")
    shared = {i["assureur"]: a.drop(columns="assureur") for a, i in zip(aggs, infos)}
    cred = pipeline.credibility_for(shared, S.key, mkt["mu"])
    try:
        cred_loo = pipeline.credibility_loo(shared, S.key)
    except ValueError:
        cred_loo = None
        st.info("Variante leave-one-out indisponible : le marché sans vous devient dégénéré à ce seuil.")
    S.market, S.cred, S.cred_loo, S.n_ins = mkt, cred, cred_loo, len(aggs)
    if S.n_ins < 5:
        st.warning(f"Hétérogénéité entre assureurs estimée sur seulement {S.n_ins} contributeurs : K et τ² sont "
                   "très incertains (lancez le bootstrap ci-dessous pour voir leur intervalle). En dessous de "
                   "5 assureurs, le modèle global est plus sûr que les bandes.")
    st.subheader("Crédibilité")
    choices = ["bandes", "global"] + (["loo"] if cred_loo else [])
    mode = st.radio("Modèle Aléa", choices, horizontal=True, label_visibility="collapsed",
                    format_func={"bandes": "Crédibilité par bandes d'âge",
                                 "global": "Globale (un θ par sexe)",
                                 "loo": "Bandes, marché sans soi (diagnostic)"}.get)
    cred_used = cred_loo if mode == "loo" else cred
    S.mu_alea = cred_used["mu_bands"] if mode in ("bandes", "loo") else cred_used["mu"]
    S.cred_mode = mode
    if mode == "loo":
        st.info("Variante de contrôle : la table de marché est réajustée **sans** votre portefeuille "
                "(leave-one-out). Utile quand un assureur domine le marché, au risque de perdre la forme de sa propre expérience.")
    if mode in ("bandes", "loo"):
        kb = pd.DataFrame(cred_used["K_bands"]["per_band"]).rename(
            columns={"band": "bande", "Ep_moyen": "Ep moyen (marché)", "K": "K de la bande",
                     "tau2": "τ²", "source_tau2": "source τ²"})
        st.dataframe(kb, use_container_width=True, hide_index=True)
        st.caption(f"τ² global = {cred_used['K_bands']['tau2_global']:.4f} ; par bande, τ² estimé sur les assureurs de la "
                   "bande avec repli sur la valeur globale quand elle est instable. "
                   "Repli sur le θ global du sexe si la bande compte moins de 20 décès attendus.")
        tb = cred_used["theta_bands"][["sex", "band", "D", "Ep", "theta_obs", "Z", "theta", "theta_lo", "theta_hi", "repli", "theta_retenu"]].rename(columns={
            "sex": "sexe", "band": "bande", "D": "décès", "Ep": "attendus (marché)", "theta_obs": "observé / attendu",
            "Z": "crédibilité Z", "theta": "θ bande", "theta_lo": "IC bas", "theta_hi": "IC haut",
            "repli": "repli sur global", "theta_retenu": "retenu"})
        pct = ["observé / attendu", "crédibilité Z", "θ bande", "IC bas", "IC haut", "retenu"]
        st.dataframe(tb.style.format({c: "{:.1%}" for c in pct} | {"attendus (marché)": "{:.1f}"}),
                     use_container_width=True, hide_index=True)
    else:
        st.caption(f"K = {cred['K']['K']:.0f} : estimé sur les données mutualisées (hétérogénéité réelle entre assureurs).")
        th = cred["theta"][["sex", "D", "Ep", "theta_obs", "Z", "theta", "theta_lo", "theta_hi"]].rename(columns={
            "sex": "sexe", "D": "décès", "Ep": "attendus (marché)", "theta_obs": "observé / attendu", "Z": "crédibilité Z",
            "theta": "retenu", "theta_lo": "IC bas", "theta_hi": "IC haut"})
        st.dataframe(th.style.format({c: "{:.1%}" for c in ["observé / attendu", "crédibilité Z", "retenu", "IC bas", "IC haut"]} | {"attendus (marché)": "{:.1f}"}),
                     use_container_width=True, hide_index=True)
    if st.button("Intervalle de confiance 95 % — bootstrap de bout en bout (~200 réajustements)"):
        with st.spinner("Bootstrap : marché, K et crédibilité réajustés sur chaque rééchantillon…"):
            S.boot = bootstrap.bootstrap_ic(shared, S.key, n_iter=200, seed=0)
    boot = S.get("boot")
    if boot:
        st.caption(f"Bootstrap ({boot['n_iter']} itérations) : τ² ∈ [{boot['tau2_ic'][0]:.4f}, {boot['tau2_ic'][1]:.4f}], "
                   f"K ∈ [{boot['K_ic'][0]:.0f}, {boot['K_ic'][1]:.0f}] à 95 %. "
                   "Le ruban ci-dessous inclut l'incertitude sur la table de marché et sur K, pas seulement celle du θ.")
    sex = st.radio("Sexe", ["M", "F"], horizontal=True, format_func={"M": "Hommes", "F": "Femmes"}.get)
    ages = np.arange(20, 81)
    own = experience.fit_relative_glm(S.cells, REF_MU)
    own_mu = experience.to_mu_lookup(own["table"], REF_MU)
    fig = go.Figure()
    if boot:
        key = "mu_bands" if mode in ("bandes", "loo") else "mu_glob"
        lo, hi = boot[f"{key}_lo"][sex][ages], boot[f"{key}_hi"][sex][ages]
        fig.add_trace(go.Scatter(x=ages, y=hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ages, y=lo, fill="tonexty", line=dict(width=0), name="IC bootstrap 95 %",
                                 fillcolor="rgba(31,78,121,0.18)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ages, y=REF_MU[sex][ages], name="Table OMS (population)", line=dict(color="#e69500", dash="dash")))
    fig.add_trace(go.Scatter(x=ages, y=mkt["mu"][sex][ages], name="Table de marché (mutualisée)", line=dict(color="#7f7f7f")))
    fig.add_trace(go.Scatter(x=ages, y=own_mu[sex][ages], name="Expérience propre seule", line=dict(color="#9ecae1")))
    fig.add_trace(go.Scatter(x=ages, y=S.mu_alea[sex][ages],
                             name={"bandes": "Aléa : bandes", "global": "Aléa : global", "loo": "Aléa : bandes, marché sans soi"}[mode],
                             line=dict(color="#1f4e79", width=3)))
    if CIMA is not None:
        cm = mu_lookup(CIMA)
        fig.add_trace(go.Scatter(x=ages, y=cm[sex][ages], name="Table CIMA", line=dict(color="red")))
    if show_truth and S.key in NAMES:
        tm = pd.read_csv(SAMPLES / f"verite_mortalite_{S.key}.csv")
        fig.add_trace(go.Scatter(x=ages, y=tm[f"mu_{sex}"].to_numpy()[ages], name="Vérité (démo)", line=dict(color="green", dash="dot")))
        tmu = {"M": tm["mu_M"].to_numpy(), "F": tm["mu_F"].to_numpy()}
        errs = {n: pipeline.weighted_log_error(mu, tmu, mkt["cells"]) for n, mu in
                {"Table OMS": REF_MU, "Expérience propre seule": own_mu, "Table de marché": mkt["mu"],
                 "Aléa (global)": cred["mu"], "Aléa (bandes)": cred["mu_bands"],
                 "Aléa (bandes, marché sans soi)": cred_loo["mu_bands"]}.items()}
        st.dataframe(pd.DataFrame({"table": errs.keys(), "erreur moyenne vs vérité": [f"{v:.1%}" for v in errs.values()]}),
                     hide_index=True)
    fig.update_layout(yaxis_type="log", yaxis_title="Force de mortalité (échelle log)", xaxis_title="Âge", height=480)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 6. Tarification
elif step == STEPS[5]:
    need("cred")
    st.header("6. Impact tarifaire")
    c1, c2, c3, c4, c5 = st.columns(5)
    sex = c1.selectbox("Sexe", ["M", "F"], format_func={"M": "Homme", "F": "Femme"}.get)
    age = c2.number_input("Âge", 18, 70, 40)
    term = c3.number_input("Durée (ans)", 1, 30, 10)
    cap = c4.number_input("Capital (FCFA)", 100_000, 100_000_000, 5_000_000, step=500_000)
    rate = c5.number_input("Taux technique", 0.0, 0.1, 0.035, step=0.005, format="%.3f",
                           help="Hypothèse à aligner sur le taux maximal autorisé par le code CIMA.")
    tables = {"Table OMS (population)": REF_MU, "Table de marché": S.market["mu"], "Aléa : table retenue": S.mu_alea}
    if CIMA is not None:
        tables["Table CIMA"] = mu_lookup(CIMA)
    rows = pd.DataFrame(pricing.compare(tables, sex, int(age), int(term), float(cap), float(rate)))
    base = rows.loc[rows["table"] == "Table OMS (population)", "prime_annuelle"].iloc[0]
    rows["écart vs OMS"] = (rows["prime_annuelle"] / base - 1).map("{:+.1%}".format)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if CIMA is None:
        st.info("Table CIMA non chargée : déposer data/reference/cima.csv pour l'ajouter à la comparaison (voir SOURCES.md).")
    if "boot" in S:
        b = S.boot
        key = "mu_bands" if S.get("cred_mode") in ("bandes", "loo") else "mu_glob"
        plo = pricing.term_premium(b[f"{key}_lo"][sex], int(age), int(term), float(cap), float(rate))["prime_annuelle"]
        phi = pricing.term_premium(b[f"{key}_hi"][sex], int(age), int(term), float(cap), float(rate))["prime_annuelle"]
        st.caption(f"Incertitude de bout en bout (bootstrap 95 %) sur la prime retenue : "
                   f"{report.fmt_num(plo)} à {report.fmt_num(phi)} FCFA.")
        S.pricing_case["prime_ic"] = [float(plo), float(phi)]
    S.pricing_case = {"libelle": f"{'homme' if sex == 'M' else 'femme'} de {age} ans, {term} ans, capital {report.fmt_num(cap)} FCFA, taux {report.fmt_num(rate * 100, 1)} %",
                      "prime_retenue": float(rows.loc[rows["table"] == "Aléa : table retenue", "prime_annuelle"].iloc[0]),
                      "prime_ref": float(base)}

# ------------------------------------------------------------------ 7. Note technique
elif step == STEPS[6]:
    need("cred", "pricing_case")
    st.header("7. Note technique assistée")
    own = experience.fit_relative_glm(S.cells, REF_MU)
    mode = S.get("cred_mode", "global")
    cred_used = S.cred_loo if mode == "loo" else S.cred
    F = facts.build(S.name, S.q_summary, own, cred_used, S.n_ins, S.pricing_case, mode)
    with st.expander("Faits calculés transmis au rédacteur (seule source autorisée)", expanded=False):
        st.dataframe(pd.DataFrame([{"fait": v["libellé"], "valeur": v["texte"]} for v in F.values()]), hide_index=True,
                     use_container_width=True)
    c1, c2 = st.columns(2)
    if c1.button("Rédiger (modèle déterministe)"):
        S.draft, S.draft_engine = report.template_note(F), "rédacteur déterministe"
    # Option désactivée en ligne (ALEA_ENABLE_LLM=0) : trop lente sur les processeurs gratuits
    if os.environ.get("ALEA_ENABLE_LLM", "1") == "1" and c2.button(f"Rédiger avec l'IA locale ({report.LLM_NAME}) — expérimental, lent sur processeur"):
        with st.spinner("Rédaction par le modèle de langage local (processeur)…"):
            try:
                S.draft, S.draft_engine = report.llm_note(F), report.LLM_NAME
            except Exception as e:  # noqa: BLE001
                st.error(f"Modèle indisponible ({e}). Utilisez le rédacteur déterministe.")
    if "draft" in S:
        st.caption(f"Rédigé par : {S.draft_engine}. Vous pouvez modifier le texte ; le garde-fou se réapplique.")
        text = st.text_area("Projet de note", S.draft, height=380)
        bad = report.guard(text, F)
        if bad:
            st.error(f"Garde-fou : {len(bad)} nombre(s) non tracé(s) vers un calcul : {', '.join(bad)}. Corrigez avant validation.")
        else:
            st.success("Garde-fou : tous les nombres du texte proviennent d'un calcul tracé.")
        st.divider()
        who = st.text_input("Actuaire validant")
        ok = st.checkbox("J'ai relu la note, vérifié les hypothèses et je la valide.")
        if st.button("Valider et signer", type="primary", disabled=bool(bad) or not who or not ok):
            manifest = {"portefeuille": S.name, "sha256_fichier": S.sha, "correspondance": S.mapping,
                        "journal_normalisation": S.norm_log, "décisions_qualité": S.decisions, "résumé_qualité": S.q_summary,
                        "modele_credibilite": mode,
                        "K_crédibilité": cred_used["K"], "K_bandes": cred_used["K_bands"],
                        "rédacteur": S.draft_engine, "actuaire": who,
                        "faits": {k: v["texte"] for k, v in F.items()}}
            d = audit.save_run(manifest, text + f"\n\nValidé et signé par : {who}\n",
                               {"credibilite": cred_used["theta"], "credibilite_bandes": cred_used["theta_bands"],
                                "experience": own["table"]})
            st.success(f"Note signée et archivée avec sa traçabilité complète : {d.relative_to(ROOT)}")
            st.download_button("Télécharger la note", text, file_name="note_technique.md")
            st.download_button("Télécharger le manifeste de traçabilité", json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
                               file_name="manifest.json")
