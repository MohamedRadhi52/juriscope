"""Évalue une méthode de recherche sur un jeu de questions.

Écrit les moyennes, leurs intervalles de confiance et le détail par question dans
results/<jeu>/<méthode>.json, puis affiche la ligne du tableau d'ablation.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.eval.metrics import bootstrap_ci, ndcg_at_k, recall_at_k, reciprocal_rank
from juriscope.paths import ROOT, SOURCES
from juriscope.retrieve.bm25 import BM25
from juriscope.retrieve.dense import Dense

RETRIEVERS = {"bm25": "BM25", "dense": "Dense (e5-small)"}
METRICS = {"rappel@10": recall_at_k, "mrr@10": reciprocal_rank, "ndcg@10": ndcg_at_k}
K = 10
HEADER = (
    "| Configuration | rappel@10 [IC95] | MRR@10 [IC95] | nDCG@10 [IC95] | p95 (ms) |\n"
    "|---|---|---|---|---:|"
)


def build(name: str, articles: list[dict]):
    """Méthode de recherche à évaluer ; chaque méthode s'appuie sur les précédentes."""
    if name == "bm25":
        return BM25(articles)
    return Dense.from_index()


def evaluate(retriever, questions: list[dict]) -> dict:
    details, latencies = [], []
    for question in questions:
        start = time.perf_counter()
        ranked = retriever.search(question["question"], k=K)
        latencies.append(time.perf_counter() - start)
        relevant = set(question["relevant"])
        scores = {name: metric(ranked, relevant, K) for name, metric in METRICS.items()}
        details.append({"id": question["id"], "type": question["type"], **scores, "top10": ranked})

    summary = {}
    for name in METRICS:
        values = [row[name] for row in details]
        summary[name] = {"moyenne": float(np.mean(values)), "ic95": bootstrap_ci(values)}
    p50, p95 = np.percentile(latencies, [50, 95]) * 1000
    summary["latence_ms"] = {"p50": float(p50), "p95": float(p95)}
    summary["rappel@10_par_type"] = {
        kind: float(np.mean([row["rappel@10"] for row in details if row["type"] == kind]))
        for kind in sorted({row["type"] for row in details})
    }
    return {"questions": len(details), **summary, "details": details}


def table_row(label: str, result: dict) -> str:
    cells = [label]
    for name in METRICS:
        low, high = result[name]["ic95"]
        cells.append(f"{result[name]['moyenne']:.3f} [{low:.3f}, {high:.3f}]")
    cells.append(f"{result['latence_ms']['p95']:.1f}")
    return "| " + " | ".join(cells) + " |"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.eval.run_eval")
    parser.add_argument("questions", type=Path, help="fichier JSONL de questions")
    parser.add_argument("--retriever", choices=RETRIEVERS, default="bm25")
    parser.add_argument("--split", choices=["dev", "test"], help="partie du jeu à évaluer")
    args = parser.parse_args()

    # les questions hors corpus n'ont pas d'article attendu : elles servent à la génération
    questions = [
        q
        for q in read_jsonl(args.questions)
        if q["relevant"] and (args.split is None or q["split"] == args.split)
    ]
    result = evaluate(build(args.retriever, load_corpus()), questions)
    result["corpus"] = json.loads(SOURCES.read_text())

    name = f"{args.questions.stem}-{args.split}" if args.split else args.questions.stem
    out = ROOT / "results" / name / f"{args.retriever}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{out.relative_to(ROOT)} ({result['questions']} questions)\n")
    print(HEADER)
    print(table_row(RETRIEVERS[args.retriever], result))


if __name__ == "__main__":
    main()
