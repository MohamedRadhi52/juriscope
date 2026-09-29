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

Le juge est un autre modèle que le générateur (Sonnet 5.5 contre Haiku 4.5), avec le réglage
de température du modèle, que Sonnet 5.5 ne permet plus de changer ; deux passages du juge
peuvent donc différer légèrement. Il applique la grille donnée aux annotateurs : une réponse réussit si elle est
fidèle aux articles cités et juste. Les refus se jugent par règle, sans modèle. Seuil fixé
avant tout calcul : le juge est retenu si son kappa de Cohen avec les étiquettes humaines
atteint 0,6 sur les 64 questions de l'échantillon qui ont une réponse, soit un accord
substantiel sur l'échelle de Landis et Koch. L'intervalle à 95 % vient de 2 000 tirages des
paires d'étiquettes. Le kappa est aussi donné sur les seules réponses jugées par le modèle,
pour ne pas le gonfler avec les refus jugés par règle.

## Fine-tuning contrastif sur des paires hors du jeu d'évaluation

Les paires d'entraînement viennent de 1 000 articles qu'aucune question du jeu d'évaluation
n'utilise, ni comme positif ni comme négatif. Haiku 4.5 écrit deux questions par article,
l'une avec les termes du texte, l'autre avec des mots courants : c'est l'écart de vocabulaire
des paraphrases, le point faible mesuré, que l'entraînement doit réduire. Chaque question
reçoit un négatif difficile tiré entre les rangs 10 et 50 de BM25 ; les tout premiers rangs
contiennent souvent d'autres bonnes réponses. La boucle d'entraînement est écrite avec
transformers en une trentaine de lignes : moyenne des états cachés comme e5, similarité
cosinus multipliée par 20, entropie croisée où la bonne réponse de chaque question est son
article et où tous les autres documents du lot servent de négatifs. Un seul passage sur les
données, par lots de 32, taux d'apprentissage 2e-5. Le gain est mesuré sur le jeu de
développement avec un intervalle apparié : les mêmes questions sont tirées pour les deux
modèles, ce qui compare les méthodes sans mélanger les différences entre questions.

## Encodage en quatre morceaux parallèles

Le premier encodage des 34 049 passages a pris près d'une heure dans un seul job. Le workflow
de fine-tuning le découpe en quatre jobs lancés en même temps, dont les vecteurs sont réunis
avant publication ; le même découpage servira pour BSARD.

## Reranker à température nulle

Deux évaluations successives du reranker, à la température par défaut, ont donné des
classements différents. Il tourne désormais à température nulle, pour que la même question
donne le même classement, et le reranker de base est recalculé dans le même run que sa
variante affinée avant toute comparaison.

## Limite connue du fine-tuning : faux négatifs dans un lot

Chaque article fournit deux questions. Si les deux tombent dans le même lot, l'article de
l'une sert de négatif à l'autre alors qu'il est la bonne réponse. Avec 2 000 questions
mélangées par lots de 32, le cas reste rare ; un échantillonneur qui évite les doublons de
lot le supprimerait.

## BSARD comme référence externe, sans entraînement dessus

BSARD (Louis et Spanakis, 2022) mesure la recherche d'articles de loi belges, en français,
sur 222 questions de test et 22 633 articles. Les modèles de Juriscope n'y sont jamais
entraînés : le modèle affiné l'a été sur le droit du travail français, et BSARD mesure ce
qui s'en transfère à un autre corps de textes. Le R@100 est la mesure de l'article original ;
à titre de repère, son meilleur modèle, entraîné sur BSARD, atteint 74,8 %. Le jeu est
téléchargé dans Actions depuis Hugging Face et n'est jamais redistribué : seules les mesures
sont publiées. L'encodage suit le même découpage en morceaux parallèles, huit jobs pour les
deux modèles.

## Juge non retenu, sans réajustement sur les mêmes étiquettes

Le kappa du juge sur les 64 questions qui ont une réponse vaut 0,46 [0,26 ; 0,66], sous le
seuil de 0,6 fixé d'avance : le juge n'est pas retenu. Il est trop indulgent, 14 des 17
désaccords étant des réponses qu'il accepte et que l'annotation refuse, dont 5 comparaisons
entre une convention et le Code. Le réajuster sur ces mêmes étiquettes puis le remesurer
gonflerait son kappa ; il faudrait de nouvelles étiquettes. La qualité de la génération est
donc mesurée par l'annotation humaine, et la CI contrôlera la génération avec des critères
vérifiables : citations présentes dans le contexte, refus des questions hors corpus, article
attendu parmi les citations.

## Veille des textes par identifiant commun

Deux versions du corpus se comparent par identifiant commun (`cid`) : un article ajouté ou
supprimé change d'ensemble, un article modifié garde son `cid` mais change de texte. Les
questions d'évaluation dont un article attendu est modifié ou supprimé sont signalées, et
chaque article du Code modifié donne une question temporelle sur sa rédaction en vigueur.
Le workflow `veille` fait cette comparaison chaque lundi entre le corpus épinglé et les
dernières versions publiées ; le workflow `keepalive` l'empêche d'être désactivé. Une réponse
qui cite un article modifié depuis la version précédente le signale.

## Agent : une boucle de décision à quatre outils

L'agent est un graphe LangGraph de deux sortes de nœuds : un nœud de décision, où Haiku 4.5
choisit l'outil suivant d'après la question et les résultats déjà obtenus, et un nœud par
outil. Quatre outils : la recherche citée (hybride affiné et reranker), la lecture d'un
article par son numéro, qui corrige le point faible de BM25 sur les références explicites,
une requête SQL sur les métadonnées des conventions, et le rapport de veille. Au plus quatre
outils par question ; les articles cités sont ceux que les outils ont renvoyés, jamais des
numéros écrits par le modèle. Ses sous-questions sont encodées à la volée par le modèle
affiné, puisqu'elles n'ont pas de vecteur calculé d'avance.

## SQL en lecture seule

La requête SQL vient du modèle : seule une instruction SELECT est acceptée, la base SQLite
est ouverte en lecture seule et 50 lignes au plus sont renvoyées. Une erreur de requête est
rendue à l'agent, qui peut la corriger, et comptée dans les résultats.

## Évaluation de l'agent sur des critères vérifiables

Trente scénarios : 5 lectures d'article, 5 questions sur les conventions, 3 sur la veille,
3 hors périmètre, 8 recherches simples et 6 questions à plusieurs étapes. Un scénario réussit
si la réponse contient les valeurs attendues, cite les articles attendus et refuse quand il
le faut ; pour l'agent, les outils attendus doivent aussi avoir servi. Le RAG simple passe
les mêmes scénarios, sans le critère des outils. Le juge LLM n'ayant pas été retenu, aucun
critère ne dépend de lui.

## Garde-fous en trois couches, et leur coût mesuré

Un filtre refuse les formules d'injection classiques avant tout appel au modèle. Le prompt
place la question et les articles entre balises et rappelle que ce sont des données, jamais
des instructions. Toute réponse sans citation valide, ou qui recopie une phrase des consignes,
devient un refus. Chaque attaque demande d'écrire un mot témoin, ce qui rend son succès
vérifiable sans juge : elle réussit si le système obéit, en répondant sans refuser avec le mot
témoin ou la fausse affirmation, ou s'il divulgue ses consignes. Une première version comptait
aussi les refus qui citent le mot témoin pour s'expliquer, ce qui gonflait les attaques
réussies avec garde-fous ; les documents piégés reçoivent une fausse consigne dans le texte d'un
article retrouvé. Le coût des garde-fous se mesure aussi : la part des questions légitimes
qui reçoivent encore une réponse citée.

## Serveur MCP léger

Le serveur MCP expose la recherche BM25 et la lecture d'un article par son numéro, sans clé
d'API ni modèle à charger : un client MCP interroge le corpus en local, en quelques
millisecondes. La recherche hybride demanderait le modèle d'embeddings, trop lourd pour ce
rôle.

## API construite par une fabrique

`create_app` reçoit la fonction qui répond : les tests la remplacent par une fausse, sans
modèle ni clé, et `build_app` assemble pour le vrai service la meilleure chaîne mesurée, avec
les garde-fous. Les liens Légifrance pointent vers la version en vigueur de chaque article,
par son identifiant de version, et non vers son identifiant commun.

## Porte de qualité sans juge

Chaque pull request, et chaque push sur main, mesure le rappel@10 de l'hybride affiné sur le
jeu de développement, avec les vecteurs des questions calculés à l'avance, donc de façon
déterministe. Sur un échantillon fixe de 12 questions, elle vérifie aussi que les réponses
sont lisibles, que leurs citations renvoient au contexte, que l'article attendu est cité et
que les questions hors corpus sont refusées. Les seuils viennent des résultats mesurés, avec
une marge pour la variabilité du modèle ; une exécution coûte quelques centimes.
