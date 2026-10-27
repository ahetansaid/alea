# Monte-Carlo adversarial : où Aléa casse

6 marchés par scénario. Erreur logarithmique absolue moyenne (pondérée exposition, 25-70 ans), hors cellules où la méthode est indisponible. Plus bas = mieux.


| Scénario | Assureur | Décès moy. | Bandes en repli | Table OMS seule | Expérience propre | Table de marché | Aléa global | Aléa bandes | Aléa LOO |
|---|---|---|---|---|---|---|---|---|---|
| S1 marché à 2 assureurs | A | 55 | 3.7 | 38.5% | 25.4% | 34.9% | 33.3% | 33.9% | n/a |
| S1 marché à 2 assureurs | B | 14 | 2.8 | 60.8% | 51.5% | 33.3% | 35.3% | 35.6% | n/a |
| S2 formes extrêmes | A | 240 | 1.0 | 37.8% | 11.0% | 15.0% | 10.0% | 12.3% | 15.6% |
| S2 formes extrêmes | B | 167 | 2.7 | 102.7% | 18.9% | 82.3% | 88.0% | 86.1% | 103.4% |
| S2 formes extrêmes | C | 107 | 3.0 | 56.6% | 11.9% | 70.5% | 69.9% | 71.4% | 95.4% |
| S2 formes extrêmes | D | 50 | 3.5 | 71.5% | 15.4% | 49.8% | 48.0% | 48.4% | 51.4% |
| S2 formes extrêmes | E | 26 | 3.0 | 28.7% | 30.3% | 38.3% | 38.2% | 38.2% | 39.7% |
| S2 formes extrêmes | F | 18 | 3.0 | 37.8% | 23.2% | 15.0% | 13.5% | 13.5% | 13.7% |
| S3 très petits porteurs | A | 13 | 3.0 | 38.2% | 34.8% | 32.5% | 32.5% | 32.5% | 46.1% |
| S3 très petits porteurs | B | 10 | 2.7 | 47.5% | 55.7% | 35.7% | 35.7% | 35.7% | 40.5% |
| S3 très petits porteurs | C | 8 | 2.2 | 29.1% | 41.5% | 34.3% | 34.3% | 34.3% | 33.9% |
| S3 très petits porteurs | D | 6 | 0.0 | 63.0% | 325.6% | 42.7% | 42.7% | 42.7% | 44.5% |
| S3 très petits porteurs | E | 5 | 0.0 | 28.7% | 325.2% | 34.2% | 34.2% | 34.2% | 37.8% |
| S4 marché dominé | Dom | 846 | 0.0 | 76.2% | 6.1% | 6.8% | 6.6% | 7.1% | 66.6% |
| S4 marché dominé | b1 | 37 | 3.2 | 38.1% | 21.0% | 43.6% | 43.4% | 43.6% | 46.2% |
| S4 marché dominé | b2 | 26 | 3.0 | 38.1% | 37.9% | 43.6% | 44.0% | 43.8% | 45.4% |
| S4 marché dominé | b3 | 18 | 3.0 | 45.0% | 36.2% | 34.3% | 34.3% | 34.4% | 35.0% |
| S4 marché dominé | b4 | 11 | 3.0 | 38.1% | 58.3% | 43.6% | 43.5% | 43.7% | 43.9% |

## Incidents

- Gardes-fous déclenchés sur un marché complet : 0. - Leave-one-out dégénéré : 0 tirages (assureur).
- Là où Aléa (bandes) perd de plus de 25 % face à la meilleure autre méthode :
  - S1 marché à 2 assureurs / A : 33.9% contre 25.4% pour la meilleure alternative
  - S2 formes extrêmes / B : 86.1% contre 18.9% pour la meilleure alternative
  - S2 formes extrêmes / C : 71.4% contre 11.9% pour la meilleure alternative
  - S2 formes extrêmes / D : 48.4% contre 15.4% pour la meilleure alternative
  - S2 formes extrêmes / E : 38.2% contre 28.7% pour la meilleure alternative
  - S4 marché dominé / b1 : 43.6% contre 21.0% pour la meilleure alternative

Durée : 339 s.