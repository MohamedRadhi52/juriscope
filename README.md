# Juriscope

Assistant qui répond aux questions de droit du travail (Code du travail et conventions
collectives) en citant l'article exact, refuse quand la réponse n'est pas dans le corpus,
et repère les textes modifiés d'une version à l'autre.

Projet en cours de construction. Le cadrage est dans [docs/cadrage.md](docs/cadrage.md) et
les choix techniques dans [docs/DECISIONS.md](docs/DECISIONS.md).

## Installation

Prérequis : Python 3.14 et `make`.

```bash
make install   # crée .venv, installe les dépendances et le hook pre-commit
make test      # tests unitaires
make lint      # ruff
make data      # télécharge et découpe le corpus (environ 35 Mo)
make test-corpus  # vérifie des articles connus dans le corpus réel
make annotate  # valide à la main un échantillon du jeu d'évaluation
```

## Données

Le corpus vient des bases LEGI (codes) et KALI (conventions collectives) de la DILA,
publiées sous Licence Ouverte d'Etalab et extraites en JSON par la Fabrique numérique des
ministères sociaux dans les paquets npm
[`@socialgouv/legi-data`](https://www.npmjs.com/package/@socialgouv/legi-data) et
[`@socialgouv/kali-data`](https://www.npmjs.com/package/@socialgouv/kali-data). Les versions
utilisées sont épinglées dans [data/sources.json](data/sources.json).

| Corpus (versions épinglées) | Articles en vigueur |
|---|---:|
| Code du travail (articles L, R, D et annexes) | 11 595 |
| 10 conventions collectives, texte de base et textes attachés | 12 804 |
| Total | 24 399 |

Un article fait 491 caractères en médiane, 3 465 au 95e centile et jusqu'à 143 430 pour
certaines annexes. 228 articles vides sont écartés, et 1 750 articles ont un texte identique
à un autre (clauses types sur la durée d'un accord, par exemple).

## Jeu d'évaluation

Les questions sont générées par Mistral à partir d'articles tirés au hasard, par partie du
Code et par convention. L'article source sert de vérité terrain, ce qui dispense d'annoter
pour mesurer la recherche. Six types sont couverts : questions factuelles, paraphrases sans
les mots du texte, questions sur deux articles voisins, comparaisons entre une convention et
le Code, et questions hors corpus tirées du Code de la sécurité sociale, pour lesquelles on
attend un refus.

Chaque question passe des vérifications automatiques : l'extrait cité doit figurer mot pour
mot dans l'article, la question ne doit pas recopier le texte, et une paraphrase doit s'en
éloigner vraiment. Le jeu est ensuite séparé en développement (60 %) et test (40 %), commité
par le workflow `evalset` avant tout réglage de la recherche, et un échantillon de 80
questions est relu à la main selon [docs/eval_guidelines.md](docs/eval_guidelines.md).

## Premiers résultats

Jeu pilote de 30 questions (`data/questions/pilote.jsonl`), BM25 sur les 24 399 articles,
intervalles de confiance à 95 % par bootstrap, latence de la recherche seule par question :

| Configuration | rappel@10 [IC95] | MRR@10 [IC95] | nDCG@10 [IC95] | p95 (ms) |
|---|---|---|---|---:|
| BM25 | 0.567 [0.400, 0.717] | 0.286 [0.161, 0.430] | 0.345 [0.219, 0.482] | 1.5 |

Ces chiffres donnent un ordre de grandeur, en attendant le jeu d'évaluation complet.
Le premier diagnostic est déjà net. Sur les 11 questions ratées qui attendent un seul
article, 9 ont en tête un article de convention qui reprend la règle du Code (la
métallurgie surtout) : la vérité terrain ne retient que l'article du Code, et le jeu
d'évaluation devra préciser la source attendue. Les autres échecs viennent du vocabulaire :
"CSE" contre "comité social et économique", "mineur" contre "jeunes travailleurs", ce que
la recherche dense devrait rattraper. Enfin, une question qui cite un numéro d'article
remonte d'abord les articles qui citent ce numéro : une résolution directe des références
est à prévoir.

```bash
make eval   # recalcule la ligne BM25 et écrit results/pilote/bm25.json
```
