"""Lecture des fichiers JSONL du projet, dont le corpus construit par l'ingestion."""

import json
from pathlib import Path

from juriscope.paths import CORPUS


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_corpus(path: Path = CORPUS / "articles.jsonl") -> list[dict]:
    return read_jsonl(path)
