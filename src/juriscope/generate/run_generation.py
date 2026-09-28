"""Répond aux questions de l'échantillon d'annotation et résume les traces.

Les réponses déjà écrites dans results/generation/answers.jsonl ne sont jamais refaites : ce
sont elles que l'on étiquette à la main pour valider le juge.
"""

import json

import numpy as np

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.eval.run_eval import build
from juriscope.evalset.annotate import SEED, sample
from juriscope.evalset.verify import EVAL
from juriscope.generate.pipeline import answer
from juriscope.generate.providers import anthropic_complete
from juriscope.paths import ROOT

MODEL = "claude-haiku-4-5-20251001"
OUTPUT = ROOT / "results" / "generation"


def summarize(rows: list[dict]) -> dict:
    """Mesures automatiques : refus, citations, latence et coût. La justesse vient du juge."""
    inside = [r for r in rows if r["relevant"]]
    outside = [r for r in rows if not r["relevant"]]
    answered = [r for r in rows if not r["refus"]]
    totals = [r["latence_ms"]["total"] for r in rows]
    return {
        "questions": len(rows),
        "reponses_illisibles": sum(not r["lisible"] for r in rows),
        "refus_corrects": sum(r["refus"] for r in outside) / len(outside),
        "refus_a_tort": sum(r["refus"] for r in inside) / len(inside),
        "citations_dans_le_contexte": sum(
            r["citations_hors_contexte"] == 0 and bool(r["citations"]) for r in answered
        )
        / len(answered),
        "article_attendu_cite": sum(bool(set(r["citations"]) & set(r["relevant"])) for r in inside)
        / len(inside),
        "latence_p50_s": float(np.percentile(totals, 50)) / 1000,
        "latence_p95_s": float(np.percentile(totals, 95)) / 1000,
        "cout_1000_requetes": 1000 * sum(r["cout"] for r in rows) / len(rows),
    }


def main() -> None:
    articles = load_corpus()
    by_cid = {a["cid"]: a for a in articles}
    answers = OUTPUT / "answers.jsonl"
    done = {row["id"] for row in read_jsonl(answers)} if answers.exists() else set()
    todo = [q for q in sample(read_jsonl(EVAL), 80, SEED) if q["id"] not in done]
    retriever = build("rerank", articles)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for number, question in enumerate(todo, 1):
        result = answer(question["question"], retriever, by_cid, anthropic_complete, MODEL)
        row = {"id": question["id"], "type": question["type"], "relevant": question["relevant"]}
        with answers.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row | result, ensure_ascii=False) + "\n")
        print(f"{number}/{len(todo)} {question['id']} {question['type']}")

    summary = summarize(read_jsonl(answers))
    (OUTPUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print("| Mesure | Valeur |\n|---|---:|")
    for key, value in summary.items():
        print(f"| {key} | {value:.3f} |" if isinstance(value, float) else f"| {key} | {value} |")


if __name__ == "__main__":
    main()
