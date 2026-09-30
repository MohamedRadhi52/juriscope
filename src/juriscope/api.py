"""API HTTP : POST /ask renvoie une réponse citée, avec les liens Légifrance, la latence et le
coût. Les garde-fous contre l'injection de prompt sont activés.

    make api
    curl -X POST localhost:8000/ask -H "Content-Type: application/json" \\
         -d '{"question": "Combien de jours de congés payés par mois ?"}'
"""

import functools
import json
from collections.abc import Callable

from fastapi import FastAPI
from pydantic import BaseModel

from juriscope.corpus import load_corpus
from juriscope.generate.pipeline import answer
from juriscope.generate.providers import anthropic_complete
from juriscope.paths import DATA, ROOT
from juriscope.retrieve.bm25 import BM25
from juriscope.retrieve.dense import Dense
from juriscope.retrieve.embed import live_encoder
from juriscope.retrieve.fusion import Hybrid
from juriscope.retrieve.references import References
from juriscope.retrieve.rerank import Rerank

MODEL = "claude-haiku-4-5-20251001"


class Question(BaseModel):
    question: str


def legifrance_url(article: dict) -> str:
    """Lien vers la version en vigueur de l'article sur Légifrance."""
    kind = "codes/article_lc" if article["id"].startswith("LEGIARTI") else "conv_coll/article"
    return f"https://www.legifrance.gouv.fr/{kind}/{article['id']}"


def create_app(respond: Callable[[str], dict], articles: dict) -> FastAPI:
    app = FastAPI(title="Juriscope", description="Questions de droit du travail, réponses citées.")

    @app.post("/ask")
    def ask(question: Question) -> dict:
        result = respond(question.question)
        return {
            "reponse": result["reponse"],
            "refus": result["refus"],
            "citations": [
                {"cid": cid, "titre": articles[cid]["title"], "url": legifrance_url(articles[cid])}
                for cid in result["citations"]
            ],
            "articles_modifies": result["articles_modifies"],
            "latence_ms": round(result["latence_ms"]["total"]),
            "cout_dollars": result["cout"],
        }

    return app


def build_responder() -> tuple[Callable[[str], dict], dict]:
    """Meilleure chaîne mesurée, garde-fous activés : articles cités par leur numéro en tête,
    puis hybride avec le modèle affiné, reranker et génération citée. Renvoie la fonction qui
    répond et les articles par identifiant."""
    articles = load_corpus()
    by_cid = {a["cid"]: a for a in articles}
    complete = functools.partial(anthropic_complete, temperature=0)
    dense = Dense.from_index("ft", encode=live_encoder(str(DATA / "models" / "e5-small-ft")))
    retriever = References(
        Rerank(Hybrid([BM25(articles), dense]), by_cid, complete, MODEL), articles
    )
    veille = json.loads((ROOT / "results" / "veille" / "rapport.json").read_text())
    respond = functools.partial(
        answer,
        retriever=retriever,
        articles=by_cid,
        complete=complete,
        model=MODEL,
        changed=frozenset(a["cid"] for a in veille["articles_modifies"]),
        guarded=True,
    )
    return respond, by_cid


def build_app() -> FastAPI:
    return create_app(*build_responder())
