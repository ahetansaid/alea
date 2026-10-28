# Évaluation d'Aléa sur portefeuilles fictifs

Données entièrement synthétiques, générées à partir de la table OMS du Bénin (2023) avec une vérité connue.
Les chiffres ci-dessous mesurent ce que le prototype retrouve, pas une performance sur données réelles.

## 1. Correspondance des colonnes

| Assureur | Champs correctement reconnus | Moteur |
|---|---|---|
| alpha | 8 / 8 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| beta | 8 / 8 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| gamma | 8 / 8 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| delta | 8 / 8 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |

## 2. Détection des erreurs injectées

### alpha

| Type | Injectées | Signalées | Précision | Rappel |
|---|---|---|---|---|
| birth_after_entry | 82 | 82 | 1.0 | 1.0 |
| death_without_date | 54 | 54 | 1.0 | 1.0 |
| duplicate | 136 | 136 | 1.0 | 1.0 |
| exit_before_entry | 82 | 82 | 1.0 | 1.0 |
| future_date | 82 | 82 | 1.0 | 1.0 |
| impossible_age | 82 | 82 | 1.0 | 1.0 |
| invalid_sex | 82 | 82 | 1.0 | 1.0 |
| sum_assured_typo | 109 | 103 | 1.0 | 0.945 |
| TOTAL | 709 | 703 | 1.0 | 0.992 |

### beta

| Type | Injectées | Signalées | Précision | Rappel |
|---|---|---|---|---|
| birth_after_entry | 31 | 31 | 1.0 | 1.0 |
| death_without_date | 20 | 20 | 1.0 | 1.0 |
| duplicate | 51 | 51 | 1.0 | 1.0 |
| exit_before_entry | 31 | 31 | 1.0 | 1.0 |
| future_date | 31 | 31 | 1.0 | 1.0 |
| impossible_age | 31 | 31 | 1.0 | 1.0 |
| invalid_sex | 31 | 31 | 1.0 | 1.0 |
| sum_assured_typo | 41 | 40 | 1.0 | 0.976 |
| TOTAL | 267 | 266 | 1.0 | 0.996 |

### gamma

| Type | Injectées | Signalées | Précision | Rappel |
|---|---|---|---|---|
| birth_after_entry | 5 | 4 | 1.0 | 0.8 |
| death_without_date | 3 | 3 | 1.0 | 1.0 |
| duplicate | 8 | 8 | 1.0 | 1.0 |
| exit_before_entry | 5 | 5 | 1.0 | 1.0 |
| future_date | 5 | 5 | 1.0 | 1.0 |
| impossible_age | 5 | 0 | nan | 0.0 |
| invalid_sex | 5 | 5 | 1.0 | 1.0 |
| sum_assured_typo | 7 | 7 | 1.0 | 1.0 |
| TOTAL | 43 | 42 | 1.0 | 0.977 |

### delta

| Type | Injectées | Signalées | Précision | Rappel |
|---|---|---|---|---|
| birth_after_entry | 16 | 16 | 1.0 | 1.0 |
| death_without_date | 11 | 11 | 1.0 | 1.0 |
| duplicate | 27 | 27 | 1.0 | 1.0 |
| exit_before_entry | 16 | 16 | 1.0 | 1.0 |
| future_date | 16 | 16 | 1.0 | 1.0 |
| impossible_age | 16 | 16 | 1.0 | 1.0 |
| invalid_sex | 16 | 16 | 1.0 | 1.0 |
| sum_assured_typo | 22 | 22 | 1.0 | 1.0 |
| TOTAL | 140 | 140 | 1.0 | 1.0 |

Note : l'assureur Gamma exporte ses dates avec des années à deux chiffres. Une naissance décalée de 100 ans (erreur « impossible_age ») y devient indiscernable d'une date correcte : l'erreur injectée n'est pas représentable dans ce format, d'où un rappel nul sur ce type pour Gamma.

## 3. Mutualisation : cellules supprimées avant partage

| Assureur | Partagées | Supprimées | Exposition supprimée |
|---|---|---|---|
| alpha | 114 | 21 | 130.7 |
| beta | 108 | 20 | 120.6 |
| gamma | 78 | 45 | 310.4 |
| delta | 100 | 26 | 110.7 |

## 4. Erreur des tables estimées par rapport à la vérité

Erreur logarithmique absolue moyenne, pondérée par l'exposition, âges 25 à 70 ans (plus bas = mieux).

| Assureur | Décès | table OMS (population) | expérience propre seule (GLM) | table de marché | Aléa : crédibilité globale | Aléa : crédibilité par bandes | Aléa : bandes, marché sans soi |
|---|---|---|---|---|---|---|---|
| alpha | 452 | 0.4288 | 0.0546 | 0.1061 | 0.1294 | 0.1074 | 0.1854 |
| beta | 169 | 0.3287 | 0.1974 | 0.1573 | 0.1693 | 0.1652 | 0.1788 |
| gamma | 36 | 0.1952 | 0.1439 | 0.2732 | 0.2016 | 0.2016 | 0.2064 |
| delta | 112 | 0.7136 | 0.3092 | 0.3035 | 0.3702 | 0.3725 | 0.3867 |

## 5. Prime annuelle pure — temporaire décès, homme 40 ans, 10 ans, 5 000 000 FCFA, taux 3,5 %

- **alpha** : OMS population = 29 064 FCFA ; vérité (inconnue en pratique) = 19 218 FCFA ; Aléa (global) = 17 373 FCFA ; Aléa (bandes) = 18 247 FCFA
- **beta** : OMS population = 29 064 FCFA ; vérité (inconnue en pratique) = 21 230 FCFA ; Aléa (global) = 18 542 FCFA ; Aléa (bandes) = 18 712 FCFA
- **gamma** : OMS population = 29 064 FCFA ; vérité (inconnue en pratique) = 24 246 FCFA ; Aléa (global) = 20 171 FCFA ; Aléa (bandes) = 20 171 FCFA
- **delta** : OMS population = 29 064 FCFA ; vérité (inconnue en pratique) = 16 184 FCFA ; Aléa (global) = 19 072 FCFA ; Aléa (bandes) = 18 936 FCFA

Durée totale : 162.3 s.