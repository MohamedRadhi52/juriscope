"""Évalue une méthode de recherche sur un jeu de questions.

Écrit les moyennes, leurs intervalles de confiance et le détail par question dans
results/<jeu>/<méthode>.json, puis affiche la ligne du tableau d'ablation.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from juriscope.corpus import load_corpus
from juriscope.eval.metrics import bootstrap_ci, ndcg_at_k, recall_at_k, reciprocal_rank
from juriscope.paths import ROOT, SOURCES
from juriscope.retrieve.bm25 import BM25

RETRIEVERS = {"bm25": ("BM25", BM25)}
METRICS = {"rappel@10": recall_at_k, "mrr@10": reciprocal_rank, "ndcg@10": ndcg_at_k}
K = 10
HEADER = (
    "| Configuration | rappel@10 [IC95] | MRR@10 [IC95] | nDCG@10 [IC95] | p95 (ms) |\n"
    "|---|---|---|---|---:|"
)


def evaluate(retriever, questions: list[dict]) -> dict:
    details, latencies = [], []
    for question in questions:
        start = time.perf_counter()
        ranked = retriever.search(question["question"], k=K)
        latencies.append(time.perf_counter() - start)
        relevant = set(question["relevant"])
        scores = {name: metric(ranked, relevant, K) for name, metric in METRICS.items()}
        details.append({"id": question["id"], **scores, "top10": ranked})

    summary = {}
    for name in METRICS:
        values = [row[name] for row in details]
        summary[name] = {"moyenne": float(np.mean(values)), "ic95": bootstrap_ci(values)}
    p50, p95 = np.percentile(latencies, [50, 95]) * 1000
    summary["latence_ms"] = {"p50": float(p50), "p95": float(p95)}
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
    args = parser.parse_args()

    with args.questions.open(encoding="utf-8") as f:
        questions = [json.loads(line) for line in f]
    label, retriever_class = RETRIEVERS[args.retriever]
    result = evaluate(retriever_class(load_corpus()), questions)
    result["corpus"] = json.loads(SOURCES.read_text())

    out = ROOT / "results" / args.questions.stem / f"{args.retriever}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{out.relative_to(ROOT)} ({result['questions']} questions)\n")
    print(HEADER)
    print(table_row(label, result))


if __name__ == "__main__":
    main()
