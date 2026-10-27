# Audit de confidentialité de la mutualisation

Contrôle sur les quatre portefeuilles fictifs de démonstration, seuil d'exposition minimale de 20.0 années-personnes par cellule partagée.

## 1. Petites cellules supprimées avant partage

| Assureur | Cellules partagées | Cellules supprimées | Exposition supprimée (années) | Décès supprimés |
|---|---|---|---|---|
| alpha | 114 | 21 | 130.7 | 10 |
| beta | 108 | 20 | 120.6 | 4 |
| gamma | 78 | 45 | 310.4 | 6 |
| delta | 100 | 26 | 110.7 | 7 |

**112** cellules supprimées au total par le seuil. Elles ne sont envoyées à personne : le total de marché ne les contient pas, la soustraction des autres contributeurs ne reconstitue donc rien.

Le seul levier restant est le **total auxiliaire** publié au bilan de partage (exposition et décès supprimés par assureur) : il identifie une cellule individuelle si un assureur n'a exactement **qu'une** cellule supprimée. Cas observé : 0 assureur(s). Tant que chaque assureur a plusieurs cellules supprimées, le total auxiliaire ne localize aucune cellule. Une gouvernance prudente publiera ces totaux par tranches plutôt que bruts.

## 2. Cellules à contributeur unique (le vrai risque)

Sur 114 cellules (sexe, âge) partagées par au moins un assureur, **6** n'ont qu'un seul contributeur. Pour elles, le total de marché publié à tous est exactement la donnée individuelle de cet assureur : c'est le vecteur de fuite réel, et le seuil d'exposition ne le couvre pas (une cellule à contributeur unique peut être volumineuse).

Masquage appliqué par Aléa (`pooling.mask_single_contributor`, appelé systématiquement par `pipeline.market_model`) : 6 cellules retirées du marché pour tous, soit 222.8 années d'exposition et 10 décès. Après masquage, il reste 0 cellule(s) publiée(s) à contributeur unique (contrôle : doit être 0).

## 3. Cellules à un seul décès

- Avant masquage : 69 paires (assureur, cellule) avec D = 1.
- Après masquage des cellules à contributeur unique : 65.

## 4. Attaque par double seuil (la glissade du curseur)

Deux tables de marché publiées avec des seuils différents (20 puis 60 années) donnent à soustraire : toute cellule d'un assureur partagée au premier seuil et retirée au second réapparaît exactement dans la différence. Cellules ainsi reconstituées : **40**.

| Assureur | Sexe | Âge | Exposition reconstituée | Décès reconstitués |
|---|---|---|---|---|
| gamma | M | 24 | 20.8 | 0.0 |
| gamma | M | 25 | 23.3 | 0.0 |
| gamma | M | 26 | 26.4 | 0.0 |
| gamma | M | 27 | 36.4 | 0.0 |
| gamma | M | 28 | 42.6 | 0.0 |
| gamma | M | 29 | 46.9 | 0.0 |
| gamma | M | 30 | 53.9 | 0.0 |
| gamma | M | 55 | 49.2 | 0.0 |
| gamma | M | 56 | 43.2 | 1.0 |
| gamma | M | 57 | 39.6 | 3.0 |
| gamma | M | 58 | 34.1 | 2.0 |
| gamma | M | 59 | 29.1 | 0.0 |
| gamma | M | 60 | 23.4 | 0.0 |
| gamma | F | 22 | 25.7 | 0.0 |
| gamma | F | 23 | 30.8 | 0.0 |
| gamma | F | 24 | 37.4 | 0.0 |
| gamma | F | 25 | 38.0 | 0.0 |
| gamma | F | 26 | 42.6 | 0.0 |
| gamma | F | 27 | 43.3 | 0.0 |
| gamma | F | 28 | 48.3 | 0.0 |
… et 20 autres.

**Règle de gouvernance : le seuil d'exposition minimale est une constante du marché, pas une préférence de session.** Il doit être identique chez tous les contributeurs et ne jamais varier ; sinon l'historique des publications devient un jeu de soustractions.

Un décès isolé dans une cellule à deux contributeurs ou plus reste une valeur individuelle dans un total, mais sans information auxiliaire (qui habite où), la réidentification n'est pas mécanique. Le relevé par cellule reste malgré tout sensible : le partager en comité n'est pas le publier.

## Conclusion

- Le seuil d'exposition minimale protège contre les petites cellules ; il ne protège pas contre les cellules à contributeur unique.
- Aléa masque désormais systématiquement ces cellules avant mutualisation.
- Publier le nombre de contributeurs par cellule, et trancher les totaux auxiliaires supprimés.