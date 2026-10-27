"""Rédaction assistée de la note technique, sous contrainte de traçabilité.

Le modèle de langage reçoit uniquement des faits calculés (valeurs déjà formatées). Un
garde-fou extrait ensuite chaque nombre du texte et vérifie qu'il correspond à un fait ;
tout nombre non tracé est signalé à l'actuaire. Un rédacteur déterministe sert de repli.
"""
from __future__ import annotations

import re
from functools import lru_cache

LLM_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
ALWAYS_ALLOWED = {95.0}  # niveau des intervalles de confiance, constante de méthode

NUM_RE = re.compile(r"(?<![\w])\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|(?<![\w])\d+(?:[.,]\d+)?")


def fmt_num(x: float, decimals: int = 0) -> str:
    s = f"{x:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return s


def fmt_pct(x: float, decimals: int = 0) -> str:
    return f"{fmt_num(100 * x, decimals)} %"


def _to_float(token: str) -> float:
    return float(re.sub(r"[   ]", "", token).replace(",", "."))


def allowed_numbers(facts: dict[str, dict]) -> set[float]:
    vals = set(ALWAYS_ALLOWED)
    for f in facts.values():
        for tok in NUM_RE.findall(str(f["texte"])):
            vals.add(round(_to_float(tok), 6))
    return vals


def guard(text: str, facts: dict[str, dict]) -> list[str]:
    """Nombres du texte qui ne correspondent à aucun fait calculé."""
    ok = allowed_numbers(facts)
    bad = []
    for tok in NUM_RE.findall(text):
        v = round(_to_float(tok), 6)
        if v not in ok:
            bad.append(tok.strip())
    return sorted(set(bad), key=bad.index)


def facts_block(facts: dict[str, dict]) -> str:
    return "\n".join(f"- {f['libellé']} : {f['texte']}" for f in facts.values())


def template_note(facts: dict[str, dict]) -> str:
    F = {k: v["texte"] for k, v in facts.items()}
    ic_txt = f", dans un intervalle de bootstrap à 95 % de {F['prime_ic']}" if "prime_ic" in F else ""
    return (
        f"Objet. La présente note présente l'étude d'expérience de mortalité du portefeuille {F['assureur']} "
        f"sur la période {F['periode']}.\n\n"
        f"Données. Le fichier transmis comptait {F['lignes_initiales']} lignes. Le contrôle qualité a conduit à "
        f"exclure {F['lignes_exclues']} lignes et à corriger {F['capitaux_corriges']} capitaux, après validation. "
        f"L'étude porte sur {F['exposition']} années-personnes d'exposition et {F['deces']} décès observés.\n\n"
        f"Expérience propre. Rapportée à la table de population OMS du Bénin, la mortalité observée représente "
        f"{F['ae_ref']} des décès attendus.\n\n"
        f"Crédibilité. L'expérience propre est combinée à celle du marché mutualisé ({F['n_assureurs']} assureurs, "
        f"agrégats uniquement), selon un modèle {F['modele']}. Le facteur de crédibilité retenu est {F['Z_M']} pour les hommes et {F['Z_F']} pour "
        f"les femmes. La mortalité retenue vaut {F['theta_M']} de la table de marché pour les hommes et {F['theta_F']} "
        f"pour les femmes, avec un intervalle crédible à 95 % de {F['theta_M_ic']} et {F['theta_F_ic']}.\n\n"
        f"Tarification. Pour un contrat temporaire décès type ({F['tarif_cas']}), la prime annuelle pure ressort à "
        f"{F['prime_retenue']} avec la table retenue{ic_txt}, contre {F['prime_ref']} avec la table de population, soit un "
        f"écart de {F['ecart_prime']}.\n\n"
        f"Limites. Les tables proposées constituent une étude d'aide à la décision. Leur usage tarifaire relève de "
        f"la validation de l'actuaire et des règles applicables du code CIMA."
    )


@lru_cache(maxsize=1)
def _llm():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(LLM_NAME)
    model = AutoModelForCausalLM.from_pretrained(LLM_NAME, dtype=torch.float32)
    model.eval()
    return tok, model


def llm_note(facts: dict[str, dict], max_new_tokens: int = 450) -> str:
    import torch
    tok, model = _llm()
    system = ("Tu es l'assistant d'un actuaire. Tu rédiges en français une note technique sobre, en paragraphes, "
              "sans titres numérotés ni listes numérotées. Tu n'utilises AUCUN nombre qui ne figure pas mot pour mot "
              "dans les faits fournis. Tu ne fais aucun calcul. Tu termines par un paragraphe de limites rappelant "
              "que l'actuaire valide et que l'usage tarifaire relève du code CIMA.")
    user = "Faits calculés (seule source autorisée) :\n" + facts_block(facts) + \
           "\n\nRédige la note technique de l'étude d'expérience (objet, données, expérience, crédibilité, tarification, limites)."
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=1.05)
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
