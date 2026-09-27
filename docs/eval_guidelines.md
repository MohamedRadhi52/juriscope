# Consignes de validation

Un échantillon de 80 questions, équilibré entre les types, est relu à la main. Il mesure la
qualité du jeu généré, puis servira à étiqueter les réponses qui valident le juge LLM.

```bash
make annotate   # reprend là où on s'est arrêté ; q pour quitter
```

Chaque question reçoit deux avis. En cas de doute, répondre non et laisser un commentaire.

## Question claire

Oui si la question est compréhensible sans l'article, sans ambiguïté sur ce qui est demandé,
et formulée comme un salarié ou un employeur pourrait le faire. Non si elle suppose d'avoir
lu l'article, mélange deux sujets sans lien ou reste vague. Une question multi-articles peut
avoir deux volets liés : c'est attendu pour ce type.

## Réponse attendue correcte

Pour une question qui s'appuie sur un ou deux articles : oui si la réponse attendue est
exacte et se trouve bien dans les articles affichés. Non si elle est fausse, trompeuse par
omission, ou demande un autre texte.

Pour une question hors corpus : oui si ni le Code du travail ni les conventions retenues ne
permettent d'y répondre, par exemple parce qu'elle relève de la sécurité sociale. Non sinon.
