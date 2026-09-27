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
make data      # télécharge le corpus (environ 35 Mo)
```

## Données

Le corpus vient des bases LEGI (codes) et KALI (conventions collectives) de la DILA,
publiées sous Licence Ouverte d'Etalab et extraites en JSON par la Fabrique numérique des
ministères sociaux dans les paquets npm
[`@socialgouv/legi-data`](https://www.npmjs.com/package/@socialgouv/legi-data) et
[`@socialgouv/kali-data`](https://www.npmjs.com/package/@socialgouv/kali-data). Les versions
utilisées sont épinglées dans [data/sources.json](data/sources.json).
