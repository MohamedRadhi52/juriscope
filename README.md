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
tirés au hasard, par partie du Code et par convention. L'article source sert de vérité
terrain, ce qui dispense d'annoter pour mesurer la recherche. Six types sont couverts :
questions factuelles, paraphrases sans les mots du texte, questions sur deux articles
voisins, comparaisons entre une convention et le Code, et questions hors corpus tirées du
Code de la sécurité sociale, pour lesquelles on attend un refus.

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
l'article, 19 questions qui recopient le texte, 3 paraphrases trop proches et 1 question mal
formée. La génération a consommé 193 000 jetons en entrée et 79 000 en sortie, soit moins
d'un dollar.

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
| BM25 | 0.514 [0.439, 0.588] | 0.343 [0.280, 0.409] | 0.367 [0.308, 0.428] | 0.4 | 0.00 |
| Dense (e5-small) | 0.574 [0.503, 0.649] | 0.406 [0.338, 0.478] | 0.430 [0.368, 0.497] | 31 | 0.00 |
| Hybride RRF | 0.655 [0.588, 0.726] | 0.428 [0.366, 0.494] | 0.465 [0.406, 0.524] | 44 | 0.00 |
| Hybride + reranker | 0.699 [0.635, 0.764] | 0.629 [0.560, 0.698] | 0.618 [0.555, 0.683] | 2711 | 5.84 |
| Dense affiné | 0.635 [0.561, 0.709] | 0.512 [0.444, 0.584] | 0.522 [0.455, 0.589] | 46 | 0.00 |
| Hybride RRF, dense affiné | 0.703 [0.635, 0.767] | 0.478 [0.412, 0.541] | 0.513 [0.451, 0.572] | 50 | 0.00 |
| Hybride affiné + reranker | 0.760 [0.696, 0.818] | 0.671 [0.600, 0.739] | 0.664 [0.600, 0.727] | 2037 | 5.76 |

Gain du fine-tuning, mesuré en apparié (les mêmes questions sont tirées pour les deux modèles) :

| Chaîne | rappel@10 | MRR@10 | nDCG@10 |
|---|---|---|---|
| Dense | +0.061 [-0.007, +0.125] | +0.106 [+0.045, +0.167] | +0.092 [+0.037, +0.147] |
| Hybride | +0.047 [+0.007, +0.091] | +0.050 [+0.012, +0.085] | +0.048 [+0.018, +0.076] |
| Hybride + reranker | +0.061 [+0.010, +0.115] | +0.042 [-0.006, +0.095] | +0.046 [+0.001, +0.095] |

Rappel@10 par type de question :

| Type | BM25 | Dense | Hybride + reranker | Dense affiné | Hybride affiné + reranker |
|---|---:|---:|---:|---:|---:|
| Factuelle | 0.61 | 0.73 | 0.85 | 0.75 | 0.87 |
| Multi-articles | 0.59 | 0.50 | 0.68 | 0.62 | 0.74 |
| Convention contre Code | 0.35 | 0.26 | 0.35 | 0.26 | 0.41 |
| Paraphrase éloignée | 0.11 | 0.16 | 0.26 | 0.42 | 0.53 |

L'hybride bat chaque méthode seule : BM25 retrouve les termes exacts, le dense les
reformulations, et leurs erreurs se recouvrent peu. Le reranker agit surtout sur le haut du
classement : le MRR passe de 0,43 à 0,63, au prix de 2 à 3 s de latence et d'environ 6 $
pour 1 000 requêtes. Le fine-tuning visait le point faible, les paraphrases éloignées : sur
ce type, le dense passe de 0,16 à 0,42 de rappel@10 et la meilleure chaîne de 0,26 à 0,53.
Reste la comparaison entre une convention et le Code : la meilleure chaîne retrouve
l'article de convention dans 12 cas sur 17, mais celui du Code dans 2 seulement.

## Génération citée

Les 5 meilleurs articles de l'hybride reclassé sont fournis à Haiku 4,5, qui répond en les
citant ou refuse. La mesure de référence est l'annotation humaine de l'échantillon (80
questions, 16 par type, réponses produites sans le modèle affiné) :

| Mesure humaine | Valeur [IC95] |
|---|---|
| Réponses correctes et fidèles aux articles cités | 35 / 80, soit 44 % [32 %, 55 %] |
| Parmi les questions qui ont une réponse | 20 / 64, soit 31 % [20 %, 42 %] |
| Refus corrects sur les questions hors corpus | 15 / 16 |

Sur tout le jeu de développement (165 questions), les mesures automatiques donnent
15 refus corrects sur 17 questions hors corpus, 22 refus à tort sur 148 questions qui ont une
réponse, 98 % de citations qui renvoient au contexte fourni et l'article attendu cité
dans 66 % des cas, pour une latence de 3,0 s en médiane et 5,4 s au 95e centile,
et 8,51 $ pour 1 000 requêtes, reranker compris.

Le juge LLM (Sonnet 5,5) devait prendre le relais de l'annotation. Son kappa avec les
étiquettes humaines vaut 0,46 [0,26 ; 0,66] sur les 64 questions qui ont une réponse, sous le seuil
de 0,6 fixé avant le calcul : il n'est pas retenu. Il est trop indulgent : 14 des 17
désaccords sont des réponses qu'il accepte et que l'annotation refuse. Sur le jeu de
développement, il compterait 54 % de réussite là où l'annotation en trouve 31 % sur l'échantillon.

## Référence externe : BSARD

222 questions de test et 22633 articles de loi belges, sans entraînement sur BSARD :

| Configuration | R@100 [IC95] | R@10 | MRR@100 |
|---|---|---:|---:|
| BM25 | 0.512 [0.456, 0.565] | 0.273 | 0.246 |
| Dense (e5-small) | 0.502 [0.448, 0.556] | 0.274 | 0.266 |
| Dense affiné sur le droit du travail | 0.529 [0.475, 0.583] | 0.266 | 0.267 |
| Hybride RRF, dense affiné | 0.590 [0.536, 0.643] | 0.304 | 0.293 |

Le fine-tuning sur le droit du travail français se transfère peu au droit belge : +0,027
de R@100 [-0,012 ; +0,065], un gain que l'intervalle ne distingue pas de zéro. L'hybride
gagne près de 8 points sur BM25 seul. À titre de repère, le meilleur modèle de l'article
original, entraîné sur BSARD, atteint 74,8 %.

## Agent

L'agent est un graphe LangGraph : à chaque tour, Haiku 4.5 choisit un outil d'après les
résultats déjà obtenus, au plus quatre fois, puis rédige la réponse. Ses outils sont la
recherche citée (hybride affiné et reranker), la lecture d'un article par son numéro, une
requête SQL en lecture seule sur les métadonnées des conventions, et le rapport de veille.
Sur 30 scénarios à critères vérifiables (valeurs attendues, articles cités, refus) :

| Type de scénario | Scénarios | Agent | RAG simple |
|---|---:|---:|---:|
| Lecture d'article | 5 | 5 | 5 |
| Recherche simple | 8 | 7 | 7 |
| Hors périmètre | 3 | 3 | 3 |
| Conventions (données SQL) | 5 | 5 | 1 |
| Veille | 3 | 3 | 0 |
| Plusieurs étapes | 6 | 6 | 2 |
| **Total** | **30** | **29** | **18** |

Sur les types que le RAG simple peut traiter (lecture d'article, recherche, hors périmètre),
les deux font jeu égal, 15 sur 16. L'agent gagne là où il faut des données absentes des
textes, métadonnées des conventions et veille, et sur les questions à plusieurs étapes. Il
n'a fait aucune erreur d'outil, en utilise 1,2 par question, et répond en 7,4 s au 95e
centile. Les scénarios ont été écrits en même temps que les outils, et les questions à
plusieurs étapes ne sont que six : ces chiffres montrent que l'agent fonctionne, pas l'ampleur
exacte de son avantage.

## Serveur MCP

`python -m juriscope.mcp_server` expose deux outils, `rechercher` et `lire_article`, à tout
client MCP, une fois le corpus construit par `make data`. Configuration type d'un client :

```json
{"mcpServers": {"juriscope": {"command": "/chemin/vers/juriscope/.venv/bin/python",
                              "args": ["-m", "juriscope.mcp_server"]}}}
```

## Veille des modifications

Entre les versions de fin juillet 2026 (legi-data 2.552.0, kali-data 3.485.0) et les
versions épinglées de septembre, 112 articles ont été ajoutés, 40 supprimés et 30 modifiés.
Aucune question du jeu d'évaluation ne s'appuie sur un article modifié ou supprimé : le jeu
reste valide. Les 13 articles du Code modifiés donnent autant de questions temporelles
(`data/questions/temporelles.jsonl`), et le workflow `veille` refait la comparaison chaque
lundi avec les dernières versions publiées.

```bash
make eval   # recalcule la ligne BM25 sur le jeu de développement
```
