"""Référence externe : BSARD, recherche d'articles de loi belges (Louis et Spanakis, 2022).

Le jeu est téléchargé depuis Hugging Face dans GitHub Actions et n'est pas redistribué :
seules les mesures sont publiées. Aucun modèle n'est entraîné sur BSARD.
"""

import argparse
import csv
import json
from urllib.request import Request, urlopen

import numpy as np

from juriscope.eval.metrics import bootstrap_ci, paired_gain_ci, recall_at_k, reciprocal_rank
from juriscope.paths import DATA, ROOT
from juriscope.retrieve.bm25 import BM25
from juriscope.retrieve.dense import Dense
from juriscope.retrieve.fusion import Hybrid

URL = "https://huggingface.co/datasets/maastrichtlawtech/bsard/resolve/main/{name}.csv"
BSARD = DATA / "bsard"
OUTPUT = ROOT / "results" / "bsard" / "resultats.json"


def download() -> None:
    BSARD.mkdir(parents=True, exist_ok=True)
    for name in ("articles", "questions_test"):
        request = Request(URL.format(name=name), headers={"User-Agent": "juriscope"})
        with urlopen(request, timeout=120) as response:
            (BSARD / f"{name}.csv").write_bytes(response.read())


def read_csv(name: str) -> list[dict]:
    with (BSARD / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_articles() -> list[dict]:
    """Articles au format du corpus Juriscope, pour réutiliser BM25 et le découpage en passages."""
    return [
        {
            "cid": row["id"],
            "title": f"Article {row['id']}",
            "path": ["Législation belge"],
            "text": row["article"],
            "idcc": [],
        }
        for row in read_csv("articles")
    ]


def load_questions() -> list[dict]:
    return [
        {"id": row["id"], "question": row["question"], "relevant": row["article_ids"].split(",")}
        for row in read_csv("questions_test")
    ]


def measure(retriever, questions: list[dict]) -> dict:
    """Rappel à 100 et à 10, et rang réciproque à 100, avec intervalles bootstrap."""
    rows = []
    for question in questions:
        ranked, relevant = retriever.search(question["question"], 100), set(question["relevant"])
        rows.append(
            {
                "r@100": recall_at_k(ranked, relevant, 100),
                "r@10": recall_at_k(ranked, relevant, 10),
                "mrr@100": reciprocal_rank(ranked, relevant, 100),
            }
        )
    summary = {}
    for name in rows[0]:
        values = [row[name] for row in rows]
        summary[name] = {
            "moyenne": float(np.mean(values)),
            "ic95": bootstrap_ci(values),
            "valeurs": values,
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.eval.bsard")
    parser.add_argument("--download", action="store_true", help="télécharge seulement le jeu")
    if parser.parse_args().download:
        download()
        return
    articles, questions = load_articles(), load_questions()
    bm25, dense, tuned = BM25(articles), Dense.from_index("bsard"), Dense.from_index("bsard-ft")
    retrievers = {
        "BM25": bm25,
        "Dense (e5-small)": dense,
        "Dense affiné sur le droit du travail": tuned,
        "Hybride RRF, dense affiné": Hybrid([bm25, tuned]),
    }
    results = {label: measure(retriever, questions) for label, retriever in retrievers.items()}
    base, ft = results["Dense (e5-small)"], results["Dense affiné sur le droit du travail"]
    gain = paired_gain_ci(base["r@100"]["valeurs"], ft["r@100"]["valeurs"])
    print(f"{len(questions)} questions de test, {len(articles)} articles\n")
    print("| Configuration | R@100 [IC95] | R@10 | MRR@100 |\n|---|---|---:|---:|")
    for label, result in results.items():
        low, high = result["r@100"]["ic95"]
        print(
            f"| {label} | {result['r@100']['moyenne']:.3f} [{low:.3f}, {high:.3f}] "
            f"| {result['r@10']['moyenne']:.3f} | {result['mrr@100']['moyenne']:.3f} |"
        )
    print(f"\nGain du fine-tuning sur le R@100 : {gain[0]:+.3f} [{gain[1]:+.3f}, {gain[2]:+.3f}]")
    report = {
        "questions": len(questions),
        "articles": len(articles),
        "resultats": results,
        "gain_r@100_du_fine_tuning": gain,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
