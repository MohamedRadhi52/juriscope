# Décisions

Chaque entrée donne la décision, puis sa raison.

## Corpus téléchargé depuis npm plutôt que par l'API Légifrance

Les paquets `@socialgouv/legi-data` et `@socialgouv/kali-data` publient des extractions
régulières des bases LEGI et KALI de la DILA. Chaque version npm est figée et vérifiable par
son empreinte sha512 : le corpus est reproductible, deux versions se comparent facilement
pour la veille, et il n'y a pas de compte PISTE ni de jetons OAuth à gérer comme avec l'API
Légifrance.

## L'article comme unité de découpage

L'article est l'unité que cite un juriste, celle qui porte un identifiant stable et celle
que désigne la vérité terrain. Découper plus fin casserait les citations ; regrouper
plusieurs articles diluerait la recherche.

## Identifiant commun (`cid`) comme vérité terrain

Voir [cadrage.md](cadrage.md#vérité-terrain) : le `cid` survit aux modifications d'un
article, ce qui garde le jeu d'évaluation valide quand le corpus change de version.
