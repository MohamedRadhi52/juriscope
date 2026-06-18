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

## Versions épinglées avec leur empreinte

Les versions npm utilisées sont notées dans `data/sources.json` avec leur empreinte sha512,
comme dans un fichier de verrouillage. `make data` ne télécharge que ce qui manque et
vérifie chaque archive ; `python -m juriscope.ingest --check` signale une version plus
récente sur npm, et `--update` l'épingle.

## Codes disponibles dans legi-data

La version 2.565.0 de `legi-data` contient quatre codes : travail, sécurité sociale, rural et
pêche maritime, relations entre le public et l'administration. Le Code monétaire et financier
n'y est pas. Seul le Code du travail entre dans le corpus.

## Conventions collectives retenues

Les huit branches qui couvrent le plus de salariés d'après le champ `effectif` de l'index de
`kali-data` (version 3.504.0), plus la banque et les sociétés d'assurances pour couvrir le
secteur financier.

| IDCC | Convention | Salariés couverts |
|---|---|---:|
| 1486 | Bureaux d'études techniques, ingénieurs-conseils et sociétés de conseils (Syntec) | 857 061 |
| 3248 | Métallurgie | 722 667 |
| 2216 | Commerce de détail et de gros à prédominance alimentaire | 689 830 |
| 0016 | Transports routiers et activités auxiliaires du transport | 679 524 |
| 1979 | Hôtels, cafés, restaurants (HCR) | 580 085 |
| 0413 | Établissements pour personnes inadaptées et handicapées (CCN 66) | 430 195 |
| 1090 | Services de l'automobile | 422 715 |
| 3043 | Entreprises de propreté et services associés | 367 142 |
| 2120 | Banque | 216 431 |
| 1672 | Sociétés d'assurances | 140 739 |
