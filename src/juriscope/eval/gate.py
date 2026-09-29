"""Porte de qualité des pull requests : la recherche et la génération ne doivent pas régresser.

Les seuils viennent des résultats mesurés, avec une marge pour la variabilité du modèle ; la
CI échoue en dessous. Aucun critère ne dépend du juge LLM, qui n'a pas été retenu.
"""

import functools
import sys

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.eval.run_eval import build, evaluate
from juriscope.evalset.verify import EVAL
from juriscope.generate.pipeline import answer
from juriscope.generate.providers import anthropic_complete
from juriscope.generate.run_generation import summarize

MODEL = "claude-haiku-4-5-20251001"
# mesuré : rappel 0,703 (hybride affiné), réponses lisibles 100 %, citations dans le contexte
# 98 %, article attendu cité 66 %, refus hors corpus 88 %
THRESHOLDS = {
    "rappel@10": 0.66,
    "reponses_lisibles": 1.0,
    "citations_dans_le_contexte": 0.8,
    "article_attendu_cite": 0.4,
    "refus_corrects": 0.5,
}


def sample(questions: list[dict]) -> list[dict]:
    """Échantillon fixe : les 10 premières questions du dev avec article, et 2 hors corpus."""
    dev = [q for q in questions if q["split"] == "dev"]
    return [q for q in dev if q["relevant"]][:10] + [q for q in dev if not q["relevant"]][:2]


def failures(measures: dict, thresholds: dict = THRESHOLDS) -> list[str]:
    return [name for name, minimum in thresholds.items() if measures[name] < minimum]


def main() -> None:
    articles = load_corpus()
    by_cid = {a["cid"]: a for a in articles}
    questions = read_jsonl(EVAL)
    retriever = build("hybride-ft", articles)
    retrieval = evaluate(retriever, [q for q in questions if q["split"] == "dev" and q["relevant"]])
    respond = functools.partial(
        answer,
        retriever=retriever,
        articles=by_cid,
        model=MODEL,
        guarded=True,
        complete=functools.partial(anthropic_complete, temperature=0),
    )
    rows = [{"relevant": q["relevant"]} | respond(q["question"]) for q in sample(questions)]
    generation = summarize(rows)
    measures = {
        "rappel@10": retrieval["rappel@10"]["moyenne"],
        "reponses_lisibles": 1 - generation["reponses_illisibles"] / generation["questions"],
        "citations_dans_le_contexte": generation["citations_dans_le_contexte"],
        "article_attendu_cite": generation["article_attendu_cite"],
        "refus_corrects": generation["refus_corrects"],
    }
    failed = failures(measures)
    print("| Mesure | Valeur | Seuil | |\n|---|---:|---:|---|")
    for name, minimum in THRESHOLDS.items():
        status = "échec" if name in failed else "ok"
        print(f"| {name} | {measures[name]:.3f} | {minimum:.2f} | {status} |")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
