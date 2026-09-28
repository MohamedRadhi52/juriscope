"""Réponse citée à une question : recherche, génération, vérification des citations, trace."""

import time
from collections.abc import Callable

from juriscope.generate.providers import cost, extract_json
from juriscope.retrieve.rerank import Rerank

PROMPT = """Tu es un assistant de droit du travail français. Réponds à la question uniquement à \
partir des articles numérotés ci-dessous.

Question : {question}

Articles :

{context}

Règles :
- appuie chaque affirmation sur les articles et donne leurs numéros ;
- si les articles ne permettent pas de répondre, refuse, sans compléter avec tes connaissances ;
- réponds en français, en quelques phrases, sans avis juridique personnel.

Réponds uniquement en JSON : {{"refus": false, "reponse": "...", "citations": [numéros des \
articles utilisés]}}"""
TEXT_CHARS = 1500


def answer(
    question: str,
    retriever,
    articles: dict,
    complete: Callable,
    model: str,
    k: int = 5,
    changed: frozenset = frozenset(),
):
    """Réponse, citations vérifiées et trace de la requête (latences, jetons, coût).

    changed contient les articles modifiés depuis la version précédente du corpus : ceux que
    la réponse cite sont signalés.
    """
    start = time.perf_counter()
    context = retriever.search(question, k)
    retrieved = time.perf_counter()
    listing = "\n\n".join(
        f"[{i}] {articles[cid]['title']}\n{articles[cid]['text'][:TEXT_CHARS]}"
        for i, cid in enumerate(context, 1)
    )
    generation = complete(PROMPT.format(question=question, context=listing), model)
    done = time.perf_counter()

    data = extract_json(generation["output"]) or {}
    numbers = [n for n in data.get("citations", []) if isinstance(n, int)]
    cited = [context[n - 1] for n in numbers if 1 <= n <= len(context)]
    spent = cost([generation["usage"]], model)
    if isinstance(retriever, Rerank):
        spent += cost(retriever.usage[-1:], retriever.model)
    return {
        "question": question,
        "contexte": context,
        "lisible": bool(data),
        "refus": bool(data.get("refus")),
        "reponse": data.get("reponse", ""),
        "citations": cited,
        "articles_modifies": [cid for cid in cited if cid in changed],
        "citations_hors_contexte": sum(1 for n in numbers if not 1 <= n <= len(context)),
        "latence_ms": {
            "recherche": 1000 * (retrieved - start),
            "generation": 1000 * (done - retrieved),
            "total": 1000 * (done - start),
        },
        "jetons": generation["usage"],
        "cout": spent,
    }
