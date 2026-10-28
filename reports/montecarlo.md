# Évaluation Monte-Carlo

30 marchés simulés de 6 assureurs fictifs (données propres). Erreur logarithmique absolue moyenne par rapport à la vraie mortalité, pondérée par l'exposition, âges 25 à 70 ans. Plus bas = mieux.

| Assureur | Contrats | Décès moyens | Crédibilité Z (hommes) | Table OMS seule | Expérience propre seule | Table de marché | Aléa (crédibilité globale) | Aléa (bandes d'âge) | Aléa (bandes, marché sans soi) |
|---|---|---|---|---|---|---|---|---|---|
| A | 40 000 | 445 | 42% | 42.9% | 6.4% | 5.4% | 5.8% | 5.9% | 7.2% |
| B | 15 000 | 184 | 29% | 32.9% | 10.6% | 7.2% | 6.9% | 7.5% | 7.9% |
| C | 8 000 | 95 | 20% | 68.5% | 17.2% | 33.3% | 33.4% | 32.5% | 34.9% |
| D | 5 000 | 64 | 15% | 15.8% | 15.7% | 31.1% | 30.1% | 30.1% | 32.7% |
| E | 2 500 | 33 | 8% | 19.6% | 25.0% | 19.7% | 18.6% | 18.6% | 19.2% |
| F | 1 500 | 20 | 5% | 67.4% | 37.4% | 36.7% | 37.0% | 37.0% | 37.3% |

## Nombre de marchés où chaque méthode est la meilleure

| Assureur | Aléa (bandes d'âge) | Aléa (bandes, marché sans soi) | Aléa (crédibilité globale) | Expérience propre seule | Table OMS seule | Table de marché |
|---|---|---|---|---|---|---|
| A | 5 | 6 | 4 | 9 | 0 | 6 |
| B | 3 | 6 | 11 | 7 | 0 | 3 |
| C | 0 | 1 | 0 | 28 | 0 | 1 |
| D | 0 | 0 | 0 | 17 | 13 | 0 |
| E | 0 | 2 | 9 | 9 | 5 | 5 |
| F | 0 | 1 | 6 | 18 | 0 | 5 |

Durée : 306 s.