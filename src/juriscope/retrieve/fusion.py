"""Fusion de classements par rang réciproque (RRF) et recherche hybride."""

from collections import defaultdict


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Classement fusionné : chaque liste apporte 1 / (k + rang) à chaque article.

    Seuls les rangs comptent, ce qui évite de rendre comparables les scores de BM25 et du dense.
    """
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking, 1):
            scores[cid] += 1 / (k + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


class Hybrid:
    def __init__(self, retrievers: list, depth: int = 100):
        self.retrievers, self.depth = retrievers, depth

    def search(self, query: str, k: int = 10) -> list[str]:
        return rrf([retriever.search(query, self.depth) for retriever in self.retrievers])[:k]
