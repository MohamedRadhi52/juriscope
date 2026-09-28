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

Les questions sont générées par un modèle de l'API Anthropic (Haiku 4.5) à partir d'articles
tirés au hasard, par partie du Code et par convention. L'article source sert de vérité terrain, ce qui dispense d'annoter
pour mesurer la recherche. Six types sont couverts : questions factuelles, paraphrases sans
les mots du texte, questions sur deux articles voisins, comparaisons entre une convention et
le Code, et questions hors corpus tirées du Code de la sécurité sociale, pour lesquelles on
attend un refus.

Chaque question passe des vérifications automatiques : l'extrait cité doit figurer mot pour
mot dans l'article, la question ne doit pas recopier le texte, et une paraphrase doit s'en
éloigner vraiment. Le jeu est ensuite séparé en développement (60 %) et test (40 %), commité
par le workflow `evalset` avant tout réglage de la recherche, et un échantillon de 80
questions est relu à la main selon [docs/eval_guidelines.md](docs/eval_guidelines.md).

| Type | Générées | Retenues | Dev | Test |
|---|---:|---:|---:|---:|
| Factuelle | 180 | 159 | 95 | 64 |
| Paraphrase | 40 | 31 | 19 | 12 |
| Multi-articles | 40 | 29 | 17 | 12 |
| Convention contre Code | 38 | 28 | 17 | 11 |
| Hors corpus | 40 | 29 | 17 | 12 |
| Total | 338 | 276 | 165 | 111 |

Les 62 rejets se répartissent ainsi : 39 extraits qui ne figurent pas mot pour mot dans
l'article, 19 questions qui recopient le texte, 3 paraphrases trop proches et 1 question mal formée. La
génération a consommé 193 000 jetons en entrée et 79 000 en sortie, soit moins d'un dollar.

La relecture de l'échantillon (80 questions, 16 par type) donne 65 questions claires et 71
réponses attendues correctes. Les paraphrases sont les plus fragiles : 10 sur 16 dans les
deux cas.

## Résultats sur le jeu de développement

Les mesures portent sur les 148 questions du jeu de développement qui attendent au moins un
article, avec des intervalles de confiance à 95 % par bootstrap. La latence est celle de la
recherche seule (pour le dense, l'encodage de la question est calculé à l'avance) ; le coût
est celui des appels à l'API.

| Configuration | rappel@10 [IC95] | MRR@10 [IC95] | nDCG@10 [IC95] | p95 (ms) | $ / 1 000 q |
|---|---|---|---|---:|---:|
| BM25 | 0.514 [0.439, 0.588] | 0.343 [0.279, 0.409] | 0.367 [0.308, 0.428] | 0.4 | 0.00 |
| Dense (e5-small) | 0.574 [0.503, 0.649] | 0.406 [0.338, 0.478] | 0.430 [0.368, 0.497] | 27 | 0.00 |
| Hybride RRF | 0.655 [0.588, 0.726] | 0.428 [0.366, 0.494] | 0.465 [0.406, 0.524] | 33 | 0.00 |
| Hybride + reranker | 0.699 [0.635, 0.764] | 0.628 [0.560, 0.697] | 0.618 [0.555, 0.682] | 1890 | 5.84 |

Rappel@10 par type de question :

| Type | BM25 | Dense | Hybride | Hybride + reranker |
|---|---:|---:|---:|---:|
| Factuelle | 0.61 | 0.73 | 0.81 | 0.85 |
| Multi-articles | 0.59 | 0.50 | 0.59 | 0.68 |
| Convention contre Code | 0.35 | 0.26 | 0.35 | 0.35 |
| Paraphrase éloignée | 0.11 | 0.16 | 0.21 | 0.26 |

L'hybride bat chaque méthode seule : BM25 retrouve les termes exacts, le dense les
reformulations, et leurs erreurs se recouvrent peu. Le reranker agit surtout sur le haut du
classement : le MRR passe de 0,43 à 0,63, au prix de 1,9 s de latence au 95e centile et
d'environ 6 $ pour 1 000 requêtes. Les paraphrases éloignées restent le point faible, avec un
rappel@10 de 0,26 au mieux : c'est cet écart de vocabulaire que le fine-tuning des
embeddings doit réduire. Pour les comparaisons entre une convention et le Code, le reranker
retrouve l'article de convention dans 10 cas sur 17, mais l'article du Code dans
2 seulement.

La génération est mesurée sur l'échantillon d'annotation (80 questions, 16 par type) : les 5
meilleurs articles de l'hybride reclassé sont fournis à Haiku 4.5, qui répond en les citant
ou refuse.

| Mesure | Valeur |
|---|---:|
| Refus corrects sur les questions hors corpus | 15 / 16 |
| Refus à tort sur les questions qui ont une réponse | 11 / 64 |
| Citations qui renvoient au contexte fourni | 98 % |
| Article attendu parmi les citations | 58 % |
| Latence p50 / p95 | 3.6 s / 6.0 s |
| Coût pour 1 000 requêtes, reranker compris | 8.84 $ |

Sur les 11 refus à tort, 7 viennent de la recherche : l'article attendu n'était pas parmi les
5 articles fournis, et le modèle a eu raison de refuser. La justesse des réponses sera
mesurée par un juge LLM, validé contre des étiquettes humaines.

```bash
make eval   # recalcule la ligne BM25 sur le jeu de développement
```
