"""Reclassement des meilleurs candidats par un modèle de langage, en une seule requête."""

from collections.abc import Callable

from juriscope.generate.providers import cost, extract_json

PROMPT = """Tu classes des articles de droit du travail selon leur utilité pour répondre à une \
question.

Question : {question}

Articles candidats :

{candidates}

Réponds uniquement en JSON : {{"ordre": [numéros des articles utiles, du plus utile au moins \
utile]}}"""


def parse_order(output: str, n: int) -> list[int]:
    """Numéros valides et distincts, dans l'ordre donné par le modèle."""
    order = (extract_json(output) or {}).get("ordre", [])
    return list(dict.fromkeys(i for i in order if isinstance(i, int) and 1 <= i <= n))


class Rerank:
    def __init__(self, retriever, articles: dict, complete: Callable, model: str, depth: int = 30):
        self.retriever, self.articles, self.depth = retriever, articles, depth
        self.complete, self.model = complete, model
        self.usage: list[dict] = []
        self.unparsed = 0

    def search(self, query: str, k: int = 10) -> list[str]:
        """Les candidats classés par le modèle d'abord, puis les autres dans leur ordre initial."""
        candidates = self.retriever.search(query, self.depth)
        listing = "\n\n".join(
            f"[{i}] {self.articles[cid]['title']}\n{self.articles[cid]['text'][:600]}"
            for i, cid in enumerate(candidates, 1)
        )
        answer = self.complete(PROMPT.format(question=query, candidates=listing), self.model)
        self.usage.append(answer["usage"])
        order = parse_order(answer["output"], len(candidates))
        self.unparsed += not order
        ranked = [candidates[i - 1] for i in order]
        return (ranked + [cid for cid in candidates if cid not in ranked])[:k]

    def cost(self) -> float:
        return cost(self.usage, self.model)
