"""Lecture du corpus construit par python -m juriscope.ingest."""

import json
from pathlib import Path

from juriscope.paths import CORPUS


def load_corpus(path: Path = CORPUS / "articles.jsonl") -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]
