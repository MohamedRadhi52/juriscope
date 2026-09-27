# Cadrage

## En une minute

Juriscope répond à des questions de droit du travail français à partir de deux sources :
le Code du travail en vigueur et une dizaine de conventions collectives nationales. Chaque
réponse cite les articles utilisés, avec leur numéro et un lien vers Légifrance. Quand les
articles retrouvés ne permettent pas de répondre, Juriscope le dit au lieu d'inventer. Il
signale aussi les réponses qui reposent sur un article modifié depuis la version précédente
du corpus.

Juriscope ne donne pas d'avis juridique. Il ne tranche pas un cas individuel, ne remplace ni
un avocat ni un représentant du personnel, et ne connaît ni la jurisprudence ni les accords
d'entreprise.

## Périmètre

| Inclus | Exclu |
|---|---|
| Code du travail, parties législative et réglementaire (articles L, R et D) | Autres codes : sécurité sociale, code civil, code pénal, etc. |
| Une dizaine de conventions collectives nationales : texte de base et textes attachés | Grilles de salaires des conventions, accords d'entreprise |
| Articles en vigueur à la date de la version du corpus | Jurisprudence, doctrine, circulaires, fonction publique |

Les grilles de salaires sont exclues parce qu'elles sont surtout des tableaux, renégociées
chaque année, et qu'une recherche textuelle y répond mal. Une question sur un salaire minimum
conventionnel doit donc donner un refus.

## Types de questions

| Type | Exemple | Réponse attendue |
|---|---|---|
| Factuelle | Quelle est la durée légale du travail ? | Un article |
| Multi-articles | Quelles sont les étapes d'un licenciement pour motif personnel ? | Plusieurs articles |
| Convention contre Code | La convention Syntec prévoit-elle une période d'essai plus longue que le Code pour un cadre ? | Un article de convention et un article du Code |
| Temporelle | Quelle rédaction de cet article est en vigueur aujourd'hui ? | L'article modifié entre deux versions du corpus |
| Hors corpus | Comment est calculée ma pension de retraite ? | Un refus |
| Paraphrase éloignée | Question formulée sans les mots du texte | Un article, résultats rapportés à part |

## Vérité terrain

La vérité terrain d'une question est la liste des articles qui contiennent la réponse,
désignés par leur identifiant commun Légifrance (`cid`, de la forme `LEGIARTI...` ou
`KALIARTI...`). Un article retrouvé est pertinent si son `cid` figure dans cette liste : la
recherche se mesure sans annotation manuelle.

Le `cid` reste le même quand un article est modifié, alors que l'identifiant de version
(`id`) change. Les questions restent donc valides d'une version du corpus à l'autre, et la
veille repère les articles dont la rédaction a changé.

## Métriques

| Niveau | Mesure |
|---|---|
| Recherche | rappel@10, MRR@10, nDCG@10, avec intervalle de confiance à 95 % par bootstrap |
| Génération | fidélité des citations (chaque article cité existe et fait partie du contexte fourni), justesse, refus correct |
| Juge LLM | accord et kappa de Cohen avec des étiquettes humaines, seuil fixé avant le calcul |
| Production | latence p50 et p95, coût pour 1 000 requêtes |
| Référence externe | BSARD, R@100, sans puis avec fine-tuning |

## Protocole

- Le jeu d'évaluation est séparé en développement et test. Tous les réglages se font sur le
  développement ; le test ne sert qu'aux jalons.
- Le jeu d'évaluation est figé et versionné avant tout réglage de la recherche.
- Les intervalles de confiance viennent de 2 000 tirages avec remise sur les questions
  (méthode des percentiles).
