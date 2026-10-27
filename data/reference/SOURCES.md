# Données de référence

## who_benin_2023_nqx.csv

Probabilités de décès par groupe d'âge (nqx), Bénin, 2023, par sexe.

- Source : Organisation mondiale de la santé, Global Health Observatory, indicateur `LIFE_0000000030`
  (« nqx — probability of dying between ages x and x+n »).
- API : https://ghoapi.azureedge.net/api/LIFE_0000000030?$filter=SpatialDim eq 'BEN'
- Extraction : 21/10/2026.

Il s'agit d'une mortalité **de population**, utilisée comme table de référence publique.

## Table réglementaire CIMA (à fournir)

Les valeurs des tables CIMA H et CIMA F ne sont pas publiées en ligne sous une forme exploitable.
Pour les comparer, déposer un fichier `cima.csv` dans ce dossier avec les colonnes :

```
sex,age,qx
M,0,0.0123
...
```

Aléa le détecte automatiquement et l'ajoute aux comparaisons et à la tarification.
Aucune valeur CIMA n'est inventée par le prototype.
