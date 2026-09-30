"""Articles cités par leur numéro dans la question, placés en tête de la recherche.

BM25 et le dense classent mal une référence explicite comme "L1234-1" : les articles qui
citent ce numéro passent devant l'article lui-même.
"""

import re

ARTICLE_NUMBER = re.compile(r"\b([LRD])\.?\s?(\d{4}-\d+(?:-\d+)*)", re.IGNORECASE)


def cited_numbers(text: str) -> list[str]:
    """Numéros d'articles du Code écrits dans le texte, normalisés : L. 1234-1 devient L1234-1."""
    return [f"{letter.upper()}{digits}" for letter, digits in ARTICLE_NUMBER.findall(text)]


class References:
    def __init__(self, retriever, articles: list[dict]):
        self.retriever = retriever
        self.by_number = {a["num"]: a["cid"] for a in articles if not a["idcc"]}

    def search(self, query: str, k: int = 10) -> list[str]:
        cited = [self.by_number[n] for n in cited_numbers(query) if n in self.by_number]
        return list(dict.fromkeys(cited + self.retriever.search(query, k)))[:k]
