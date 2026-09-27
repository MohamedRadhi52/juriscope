# Juriscope

Assistant qui répond aux questions de droit du travail (Code du travail et conventions
collectives) en citant l'article exact, refuse quand la réponse n'est pas dans le corpus,
et repère les textes modifiés d'une version à l'autre.

Projet en cours de construction.

## Installation

Prérequis : Python 3.14 et `make`.

```bash
make install   # crée .venv, installe les dépendances et le hook pre-commit
make lint      # ruff
```
