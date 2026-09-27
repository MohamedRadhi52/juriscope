"""Recherche lexicale BM25 sur les articles."""

import bm25s

from juriscope.retrieve.text import tokenize


def index_text(article: dict) -> str:
    """Texte indexé : chemin hiérarchique, titre, puis texte de l'article."""
    return "\n".join([*article["path"], article["title"], article["text"]])


class BM25:
    def __init__(self, articles: list[dict]):
        self.cids = [a["cid"] for a in articles]
        self.model = bm25s.BM25()
        self.model.index([tokenize(index_text(a)) for a in articles], show_progress=False)

    def search(self, query: str, k: int = 10) -> list[str]:
        """Identifiants communs des k articles les mieux classés."""
        docs, _ = self.model.retrieve([tokenize(query)], k=k, show_progress=False)
        return [self.cids[i] for i in docs[0]]
