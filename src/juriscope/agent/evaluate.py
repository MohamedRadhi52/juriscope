"""Évalue l'agent et le RAG simple sur les mêmes scénarios, avec des critères vérifiables.

Un scénario réussit si la réponse contient les valeurs attendues, cite les articles attendus
et refuse quand il le faut ; pour l'agent, les outils attendus doivent aussi avoir servi.
"""

import functools
import json
import re
import time

import numpy as np

from juriscope.agent import graph, tools
from juriscope.corpus import load_corpus, read_jsonl
from juriscope.generate.pipeline import answer
from juriscope.generate.providers import anthropic_complete, cost
from juriscope.paths import DATA, ROOT
from juriscope.retrieve.bm25 import BM25
from juriscope.retrieve.dense import Dense
from juriscope.retrieve.embed import live_encoder
from juriscope.retrieve.fusion import Hybrid
from juriscope.retrieve.rerank import Rerank
from juriscope.retrieve.text import fold

MODEL = "claude-haiku-4-5-20251001"
FT_MODEL = DATA / "models" / "e5-small-ft"
SCENARIOS = DATA / "questions" / "agent.jsonl"
OUTPUT = ROOT / "results" / "agent"


def normalize(text: str) -> str:
    """Minuscules sans accents, chiffres recollés : 857 061 et 857061 se comparent."""
    return re.sub(r"(?<=\d)[\s.\u202f\u00a0](?=\d{3}\b)", "", fold(text).lower())


def succeeded(result: dict, scenario: dict, check_tools: bool) -> bool:
    text = normalize(result["reponse"])
    return (
        all(normalize(value) in text for value in scenario["contient"])
        and set(scenario["cite"]) <= set(result["citations"])
        and result["refus"] == scenario["refus"]
        and (not check_tools or set(scenario["outils"]) <= set(result["outils"]))
    )


def main() -> None:
    articles = load_corpus()
    by_cid = {a["cid"]: a for a in articles}
    code = {a["num"]: a for a in articles if not a["idcc"]}
    usages = []

    def complete(prompt: str, model: str) -> dict:
        result = anthropic_complete(prompt, model, temperature=0)
        usages.append(result["usage"])
        return result

    dense = Dense.from_index("ft", encode=live_encoder(str(FT_MODEL)))
    retriever = Rerank(Hybrid([BM25(articles), dense]), by_cid, complete, MODEL)
    changed = frozenset(a["cid"] for a in json.loads(tools.VEILLE.read_text())["articles_modifies"])
    search = functools.partial(
        answer,
        retriever=retriever,
        articles=by_cid,
        complete=complete,
        model=MODEL,
        changed=changed,
    )

    def search_tool(question: str) -> dict:
        """Réponse citée, réduite à ce qui sert à l'agent."""
        result = search(question)
        return {
            "reponse": result["reponse"],
            "refus": result["refus"],
            "citations": result["citations"],
            "titres": [by_cid[cid]["title"] for cid in result["citations"]],
            "articles_modifies": result["articles_modifies"],
        }

    database = tools.build_database(articles)
    agent = graph.build_agent(
        graph.llm_decide(complete, MODEL),
        {
            "recherche": search_tool,
            "article": lambda n: tools.find_article(n, code),
            "conventions": lambda sql: tools.query_conventions(sql, database),
            "veille": lambda _: tools.veille_summary(),
        },
    )

    rows = []
    for scenario in read_jsonl(SCENARIOS):
        start = time.perf_counter()
        agent_result = graph.run(agent, scenario["question"])
        middle = time.perf_counter()
        rag_result = search(scenario["question"])
        rows.append(
            {
                "id": scenario["id"],
                "type": scenario["type"],
                "agent": agent_result
                | {"reussi": succeeded(agent_result, scenario, True), "latence_s": middle - start},
                "rag": {
                    "reponse": rag_result["reponse"],
                    "citations": rag_result["citations"],
                    "refus": rag_result["refus"],
                    "reussi": succeeded(rag_result, scenario, False),
                },
            }
        )
        print(scenario["id"], rows[-1]["agent"]["reussi"], rows[-1]["rag"]["reussi"], flush=True)

    kinds = sorted({row["type"] for row in rows})
    summary = {
        "scenarios": len(rows),
        "agent": float(np.mean([r["agent"]["reussi"] for r in rows])),
        "rag": float(np.mean([r["rag"]["reussi"] for r in rows])),
        "par_type": {
            k: {
                "scenarios": sum(r["type"] == k for r in rows),
                "agent": sum(r["agent"]["reussi"] for r in rows if r["type"] == k),
                "rag": sum(r["rag"]["reussi"] for r in rows if r["type"] == k),
            }
            for k in kinds
        },
        "erreurs_outils": sum(r["agent"]["erreurs_outils"] for r in rows),
        "outils_par_question": float(np.mean([len(r["agent"]["outils"]) for r in rows])),
        "latence_agent_p95_s": float(np.percentile([r["agent"]["latence_s"] for r in rows], 95)),
        "cout_total": cost(usages, MODEL),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "details.jsonl").open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (OUTPUT / "resultats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
