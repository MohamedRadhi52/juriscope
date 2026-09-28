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

## Articles en vigueur seulement

Un article du Code du travail entre dans l'index s'il est applicable à la date de la version
du code (`dateDebutVersion`). Les articles à abrogation différée, 117 dans la version
épinglée, y restent jusqu'à leur date de fin. KALI ne donne pas de dates par article : l'état
doit commencer par `VIGUEUR`, étendu ou non. Les paquets npm ne contiennent que les textes
en vigueur ; l'historique utile à la veille vient de la comparaison de deux versions, dont
les archives restent dans `data/raw`.

## Titre complet pour les articles de convention

Dans une même convention, les numéros d'articles se répètent d'un accord à l'autre (Syntec
compte plusieurs articles 3.3). Le titre cité nomme donc le texte : "Syntec (IDCC 1486),
Accord du 7 octobre 2015 relatif à la complémentaire santé, art. 3.3 : Conditions d'octroi".
Le chemin hiérarchique complet est gardé avec chaque article.

## Articles communs à deux conventions

Les 20 articles de l'accord créant l'OPCABAIA figurent dans les conventions de la banque et
des sociétés d'assurances. Ils sont fusionnés en un seul article rattaché aux deux IDCC,
pour ne pas occuper deux places dans les résultats.

## Tokenisation française pour BM25

Les accents sont retirés avant la racinisation Snowball, pour que "salariés" et "salaries"
donnent la même racine : sur 15 groupes de variantes testés (accents, pluriels), cet ordre en
réunit 11, contre 8 dans l'ordre inverse. Les particules élidées (l', qu', jusqu') et les mots vides sont
retirés. Les sigles restent tels quels et ne sont jamais des mots vides : "le CE" n'est pas
le pronom "ce". Les références d'articles sont normalisées, "L. 1234-1" et "L1234-1" donnent
le même jeton.

## Texte indexé : chemin, titre et texte

Beaucoup d'articles ne portent pas les mots de leur contexte : aucun article de la
convention Syntec ne contient "Syntec", qui n'apparaît que dans le chemin. Le texte indexé
réunit donc le chemin hiérarchique, le titre et le texte. Cette règle est fixée avant
d'avoir le jeu d'évaluation ; sa variante sans chemin sera comparée sur le jeu de
développement.

## Jeu pilote avant le jeu d'évaluation

Trente questions écrites à partir d'articles connus font tourner le banc en attendant le
jeu d'évaluation.
Aucun réglage n'est fait sur ce jeu : ses chiffres donnent un ordre de grandeur, avec des
intervalles larges, et le premier diagnostic d'erreurs.

## Questions générées par l'API Anthropic

Le plan prévoyait de confier la génération à Mistral, pour que le futur juge LLM vienne d'une
autre famille de modèles. Le forfait gratuit de Mistral n'active plus les clés API, et un
abonnement mensuel ne se justifiait pas pour quelques centaines de questions : elles sont
écrites par Haiku 4.5, le plus petit modèle de l'API Anthropic, pour moins d'un dollar.
Conséquence assumée : générateur et juge viendront du même fournisseur. Deux garde-fous
limitent le biais : le juge utilisera un autre modèle que le générateur, et il sera validé
contre des étiquettes humaines (kappa de Cohen). Mistral reste disponible comme fournisseur
(`--provider mistral`). Le tirage des articles est fixé par une graine ; le modèle exact et
les jetons consommés sont enregistrés avec chaque question.

## Six types de questions, stratifiés

| Type | Tirage | Nombre visé |
|---|---|---:|
| Factuelle, Code du travail | 15 par partie du Code (deux tiers législatifs) | 120 |
| Factuelle, convention | 6 par convention | 60 |
| Paraphrase éloignée | 5 par partie, rapportées à part | 40 |
| Multi-articles | 5 paires d'articles voisins par partie | 40 |
| Convention contre Code | 4 par convention, un article qui cite un article L | 40 |
| Hors corpus | Code de la sécurité sociale, livres III, V et VIII | 40 |

Les questions temporelles viendront de la comparaison de deux versions du corpus. Aucun
article ne sert deux fois, et les articles propres à l'outre-mer sont écartés. Leçon du jeu
pilote : une question tirée du Code ne nomme aucune convention, une question tirée d'une
convention la nomme par son nom courant.

## Questions hors corpus tirées de la sécurité sociale

Le Code de la sécurité sociale est dans `legi-data` mais pas dans le corpus : une question
écrite à partir de l'un de ses articles porte sur un sujet voisin du droit du travail, que
l'assistant doit pourtant refuser. C'est plus réaliste que des questions sans rapport.

## Vérifications automatiques

Une question est rejetée si le modèle a jugé l'article inutilisable, si elle ne tient pas en
une phrase interrogative de 5 à 45 mots, si l'extrait qui justifie la réponse ne figure pas
mot pour mot dans l'article, si elle reprend 7 mots consécutifs du texte, ou, pour une
paraphrase, si plus de 40 % de ses mots pleins figurent dans l'article. Les doublons sont
retirés. Chaque rejet est compté par motif dans `results/evalset/verification.json`.

La comparaison des extraits ignore la casse, les accents et la ponctuation, et accepte les
coupures signalées par [...] ; une question terminée par un point reçoit un point
d'interrogation. La première version, stricte sur ces détails de forme, rejetait 138
questions sur 338, dont 80 pour un simple point final ; la version actuelle en rejette 62,
dont 39 extraits qui omettent des mots sans le signaler.

## Jeu figé avant tout réglage

Le jeu est séparé en développement (60 %) et test (40 %) dans chaque type, puis commité par
le workflow `evalset`. Le générateur ne réécrit jamais une question déjà produite : relancer
le workflow complète un jeu interrompu et ne change rien à un jeu complet.

## Embeddings ouverts, calculés dans GitHub Actions

La recherche dense utilise `intfloat/multilingual-e5-small`, un modèle ouvert de 118 millions
de paramètres, plutôt qu'une API d'embeddings : pas de clé à gérer, des vecteurs
reproductibles, et le même modèle que celui qui sera affiné, ce qui rend la comparaison
entre modèle de base et modèle affiné directe. Le calcul tourne dans le workflow `embed`,
qui publie les vecteurs en asset de release ; ils portent la version du corpus et sont
refusés s'ils ne correspondent plus à `data/sources.json`. Les vecteurs des questions sont
calculés en même temps : la latence mesurée pour la recherche dense exclut donc l'encodage
de la question.

## Passages de 250 mots, meilleur passage par article

Le modèle lit au plus 512 jetons, alors que 5 % des articles dépassent 3 400 caractères.
Chaque article est découpé en fenêtres de 250 mots qui se chevauchent de 50 mots, et chaque
passage commence par le titre et la section de l'article. Un article est classé selon son
meilleur passage.

## Qdrant en mode local

Les vecteurs sont chargés dans Qdrant en mode local, sans serveur : c'est le même client
qu'en production, où il parlerait à un serveur Qdrant. Le mode local avertit au-delà de
20 000 points ; il reste assez rapide pour évaluer environ 40 000 passages.

## Fusion hybride par rang réciproque

BM25 et la recherche dense renvoient chacun 100 articles, fusionnés par RRF : chaque liste
apporte 1 / (60 + rang) à un article. Seuls les rangs comptent, ce qui évite de calibrer
des scores qui n'ont pas la même échelle. La constante 60 est la valeur usuelle de la
méthode ; elle n'est pas réglée.

## Reranker par un modèle de langage

Les 30 premiers articles de l'hybride sont reclassés par Haiku 4.5 en une seule requête :
le modèle lit la question et le début de chaque article, puis donne l'ordre des articles
utiles. Ceux qu'il écarte gardent leur ordre initial après les siens, et une réponse
illisible laisse le classement intact ; ces cas sont comptés. Le coût et la latence de cet
appel sont mesurés, car c'est le prix du gain en précision.

## Coûts en dollars

Les API facturent en dollars : les coûts sont donnés en dollars pour 1 000 requêtes,
calculés à partir des jetons réellement consommés et des tarifs publics, sans taux de
change à supposer.

## Génération citée au format JSON

Le modèle reçoit les 5 meilleurs articles de l'hybride reclassé, numérotés, et répond en JSON :
refus ou non, réponse, numéros des articles utilisés. Les numéros sont traduits en
identifiants d'articles ; un numéro qui ne correspond à aucun article du contexte est compté
comme citation invalide. Haiku 4.5 génère comme il reclasse, et le coût de chaque requête est
mesuré.

## Refuser plutôt qu'inventer

La consigne demande de refuser quand les articles ne permettent pas de répondre, sans
compléter avec les connaissances du modèle. Deux taux automatiques en découlent sur
l'échantillon d'annotation : refus corrects sur les questions hors corpus et refus à tort
sur les autres. La justesse des réponses viendra du juge LLM, validé contre les étiquettes
humaines.

## Traces de chaque requête

Chaque réponse garde ses latences (recherche, génération, total), ses jetons et son coût,
reranker compris. Les résumés donnent la latence p50 et p95 et le coût pour 1 000 requêtes.
Un journal maison suffit à ce volume ; Langfuse ou OpenTelemetry prendraient le relais en
production.

## Une même interface pour trois fournisseurs

Anthropic, Mistral et Azure OpenAI renvoient la même forme de réponse : modèle exact, texte
et jetons. Azure OpenAI est couvert par un test avec une API simulée : il suffit de définir
`AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_API_KEY`, puis de passer le nom du déploiement comme
modèle.

## Juge LLM validé avant usage, seuil fixé d'avance

Le juge est un autre modèle que le générateur (Sonnet 5.5 contre Haiku 4.5), à température
nulle, et il applique la grille donnée aux annotateurs : une réponse réussit si elle est
fidèle aux articles cités et juste. Les refus se jugent par règle, sans modèle. Seuil fixé
avant tout calcul : le juge est retenu si son kappa de Cohen avec les étiquettes humaines
atteint 0,6 sur les 64 questions de l'échantillon qui ont une réponse, soit un accord
substantiel sur l'échelle de Landis et Koch. L'intervalle à 95 % vient de 2 000 tirages des
paires d'étiquettes. Le kappa est aussi donné sur les seules réponses jugées par le modèle,
pour ne pas le gonfler avec les refus jugés par règle.
