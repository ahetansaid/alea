---
title: Aléa — actuariat augmenté
emoji: 📈
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8501
pinned: false
license: other
short_description: Actuariat augmenté — l'IA prépare, l'actuaire décide
---

# Aléa — actuariat augmenté

**L'IA prépare, l'actuaire décide.**

**Démo en ligne** : lien du Space Hugging Face (à compléter après déploiement).

En Afrique francophone (zone CIMA), l'assurance-vie est encore tarifée sur des tables de mortalité
dérivées de la population française des années 1960, et la pénétration de l'assurance plafonne
autour de 1 % du PIB. Aléa aide les actuaires à construire, à partir des données des assureurs et
**sans partager de données personnelles**, des références de mortalité locales et crédibles.

> Prototype de recherche. Toutes les données de portefeuille sont **fictives** et générées par le
> projet ; la seule donnée réelle est la table de mortalité publique de l'OMS pour le Bénin.

## Ce que fait le prototype

| Étape | Ce qui se passe | IA / méthode |
|---|---|---|
| 1. Données | Import d'un export brut d'assureur (CSV, encodage et séparateur détectés) | — |
| 2. Colonnes | Reconnaissance des colonnes hétérogènes (français/anglais) vers un schéma standard | Embeddings multilingues `paraphrase-multilingual-MiniLM-L12-v2` (Hugging Face) + profil des valeurs, affectation optimale (algorithme hongrois) |
| 3. Qualité | Doublons, dates incohérentes, âges impossibles, capitaux aberrants… avec action proposée | Contrôles de règles + **Isolation Forest** (scikit-learn) ; l'actuaire accepte ou rejette |
| 4. Expérience | Expositions et décès par âge et sexe ; mortalité en % d'une table de référence | **GLM de Poisson** (statsmodels) avec intervalles de confiance |
| 5. Mutualisation | Chaque assureur ne partage que des agrégats (exposition, décès) ; petites cellules supprimées | Table de marché ; **crédibilité Poisson-Gamma** avec hétérogénéité estimée entre assureurs |
| 6. Tarification | Prime pure d'un temporaire décès selon chaque table | Calcul actuariel classique |
| 7. Note technique | Projet de note rédigé, puis validé et signé par l'actuaire | LLM ouvert **Qwen2.5-1.5B-Instruct** exécuté en local (CPU) ; **garde-fou** qui rejette tout nombre non issu d'un calcul |

Chaque note signée est archivée avec un manifeste de traçabilité : empreinte du fichier source,
correspondance des colonnes, décisions qualité, paramètres, version du code.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt
python scripts/generate_data.py  # génère les portefeuilles fictifs
streamlit run app.py             # interface de démonstration
```

Évaluation complète contre la vérité connue des données fictives :

```bash
python scripts/evaluate.py       # écrit reports/evaluation.md
python scripts/montecarlo.py 30  # écrit reports/montecarlo.md (environ 2 min)
pytest -q                        # tests unitaires + parcours complet de l'interface
```

Coût d'exécution : nul. Tous les modèles sont ouverts et tournent en local, sans API payante.

## Évaluation

Les portefeuilles fictifs ont une mortalité **connue** et des erreurs **injectées à des positions
connues**. On mesure donc réellement :

- la part des colonnes correctement reconnues ;
- la précision et le rappel de la détection d'erreurs, par type ;
- l'écart entre chaque table estimée et la vraie mortalité (table OMS seule, expérience propre seule,
  table de marché, crédibilité Aléa) ;
- l'impact sur la prime.

Résultats détaillés : [`reports/evaluation.md`](reports/evaluation.md) (un marché de 4 assureurs, avec
erreurs injectées) et [`reports/montecarlo.md`](reports/montecarlo.md) (30 marchés de 6 assureurs, dont
trois dont la mortalité a une **forme** par âge différente de la moyenne du marché).

**En bref**

- Colonnes reconnues : 8 sur 8 pour les quatre assureurs (trois formats d'export : français, anglais, codes différents).
- Erreurs injectées détectées : précision 100 %, rappel de 97,7 % à 100 % selon l'assureur.
- Piège évité : exclure les « décès sans date » supprimerait environ 12 % des décès et sous-estimerait
  la mortalité ; Aléa propose d'imputer la date.
- Confidentialité : les cellules (sexe, âge) où un seul assureur contribue sont masquées avant
  mutualisation — un agrégat à contributeur unique est une donnée individuelle déguisée ; le seuil
  d'exposition est une constante du marché, car deux tables publiées à des seuils différents
  reconstituent 40 cellules par simple soustraction ([`reports/disclosure.md`](reports/disclosure.md)).
- Épreuve adversariale : 24 marchés hostiles (marché à deux assureurs, formes tilteées à ±0,8,
  micro-porteurs, marché dominé) — zéro plantage, garde-fous non déclenchés à tort ; la perte
  concentrée vient du **mismatch de forme** : quand la forme d'un assureur diffère du marché, la
  référence mutualisée le biasse de 40 à 90 %, d'où le diagnostic leave-one-out et le rapport
  observé/attendu par bande ([`reports/stress.md`](reports/stress.md)).
- Erreur moyenne par rapport à la vraie mortalité (Monte-Carlo, 30 marchés) :

| Assureur | Décès moyens | Table OMS seule | Expérience propre seule | Table de marché | Aléa (global) | **Aléa (bandes)** |
|---|---|---|---|---|---|---|
| 40 000 contrats | 445 | 42,9 % | 6,4 % | 5,3 % | 5,6 % | **5,3 %** |
| 15 000 contrats | 184 | 32,9 % | 10,6 % | 7,1 % | 6,7 % | **6,6 %** |
| 8 000 contrats | 95 | 68,5 % | 17,2 % | 33,4 % | 33,5 % | 33,5 % |
| 5 000 contrats | 64 | 15,8 % | 15,7 % | 31,0 % | 30,0 % | 30,2 % |
| 2 500 contrats | 33 | 19,6 % | 25,0 % | 19,6 % | 18,6 % | 18,9 % |
| 1 500 contrats | 20 | 67,4 % | 37,4 % | 36,9 % | 37,1 % | 37,1 % |

Quand le marché a une forme homogène (assureurs A, B), la crédibilité par bandes égale ou améliore la
meilleure table de référence, y compris pour l'assureur dominant. Quand le marché mélange des formes de
mortalité différentes (C, D, F), la table de marché elle-même est biaisée de 30 % et plus, et Aléa en
hérite : dans ce cas l'expérience propre seule ou la table OMS fait mieux. C'est une limite de la
référence mutualisée, pas de la crédibilité — un marché unique ne peut pas être juste pour tous. Aléa le
rend visible (rapport observé/attendu, bandes, leave-one-out) et recommande de stratifier les marchés par
produit et population.

## Données

- `data/reference/who_benin_2023_nqx.csv` : OMS, Global Health Observatory (voir `SOURCES.md`).
- `data/reference/cima.csv` : **à fournir** pour comparer avec les tables réglementaires CIMA ;
  aucune valeur CIMA n'est inventée par le projet.
- `data/samples/` : quatre assureurs fictifs (Alpha, Bêta, Gamma, Delta — ce dernier avec une forme de
  mortalité par âge différente du marché), leurs erreurs injectées et leur vraie mortalité.

## Principes

- **L'actuaire décide** : aucune table, aucun tarif, aucune note ne sort sans validation nominative.
- **Pas de donnée personnelle partagée** : la mutualisation n'utilise que des comptages agrégés.
- **Reproductibilité** : chaque résultat est rattaché à ses données, ses décisions et son code.
- **Honnêteté statistique** : l'incertitude est toujours affichée.

## Limites

Prototype sur données synthétiques. Les tables d'expérience produites sont des études d'aide à la
décision ; leur usage tarifaire relève de l'actuaire et des règles du code CIMA.
