# Évaluation Monte-Carlo

30 marchés simulés de 6 assureurs fictifs (données propres). Erreur logarithmique absolue moyenne par rapport à la vraie mortalité, pondérée par l'exposition, âges 25 à 70 ans. Plus bas = mieux.

| Assureur | Contrats | Décès moyens | Crédibilité Z (hommes) | Table OMS seule | Expérience propre seule | Table de marché | Aléa (crédibilité globale) | Aléa (bandes d'âge) | Aléa (bandes, marché sans soi) |
|---|---|---|---|---|---|---|---|---|---|
| A | 40 000 | 445 | 42% | 42.9% | 6.4% | 5.3% | 5.6% | 5.3% | 9.1% |
| B | 15 000 | 184 | 29% | 32.9% | 10.6% | 7.1% | 6.7% | 6.6% | 7.7% |
| C | 8 000 | 95 | 20% | 68.5% | 17.2% | 33.4% | 33.5% | 33.5% | 36.2% |
| D | 5 000 | 64 | 15% | 15.8% | 15.7% | 31.0% | 30.0% | 30.2% | 32.9% |
| E | 2 500 | 33 | 8% | 19.6% | 25.0% | 19.6% | 18.6% | 18.9% | 19.5% |
| F | 1 500 | 20 | 5% | 67.4% | 37.4% | 36.9% | 37.1% | 37.1% | 37.4% |

## Nombre de marchés où chaque méthode est la meilleure

| Assureur | Aléa (bandes d'âge) | Aléa (bandes, marché sans soi) | Aléa (crédibilité globale) | Expérience propre seule | Table OMS seule | Table de marché |
|---|---|---|---|---|---|---|
| A | 6 | 3 | 4 | 8 | 0 | 9 |
| B | 3 | 7 | 10 | 7 | 0 | 3 |
| C | 0 | 1 | 0 | 28 | 0 | 1 |
| D | 0 | 0 | 0 | 17 | 13 | 0 |
| E | 2 | 3 | 8 | 9 | 3 | 5 |
| F | 1 | 2 | 5 | 18 | 0 | 4 |

Durée : 594 s.