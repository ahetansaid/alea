"""Parcours complet de l'interface, comme un actuaire : chargement → note signée."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
STEPS = ["1. Données", "2. Colonnes", "3. Qualité", "4. Expérience", "5. Mutualisation", "6. Tarification", "7. Note technique"]


def click(at, label):
    for b in at.button:
        if b.label.startswith(label):
            b.click()
            return at.run()
    raise AssertionError(f"bouton introuvable : {label} ; présents : {[b.label for b in at.button]}")


def goto(at, step):
    at.sidebar.radio[0].set_value(step)
    return at.run()


def test_full_flow():
    # Sur un processeur modeste, charger PyTorch puis le modèle d'embeddings peut dépasser 4 minutes par étape.
    at = AppTest.from_file(APP, default_timeout=1800).run()
    assert not at.exception
    at = click(at, "Charger")
    assert any("lignes" in s.value for s in at.success)
    at = goto(at, STEPS[1])
    at = click(at, "Valider la correspondance")
    assert not at.exception and "canon" in at.session_state
    at = goto(at, STEPS[2])
    at = click(at, "Appliquer les décisions")
    assert "cells" in at.session_state
    at = goto(at, STEPS[3])
    assert not at.exception
    at = goto(at, STEPS[4])
    assert not at.exception and "cred" in at.session_state
    at = goto(at, STEPS[5])
    assert not at.exception and "pricing_case" in at.session_state
    at = goto(at, STEPS[6])
    at = click(at, "Rédiger (modèle déterministe)")
    assert not at.exception
    assert any("tous les nombres" in s.value for s in at.success), [e.value for e in at.error]
    at.text_input[0].input("Actuaire Test").run()
    at.checkbox[0].check().run()
    at = click(at, "Valider et signer")
    assert any("signée" in s.value for s in at.success)
