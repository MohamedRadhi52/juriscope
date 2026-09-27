"""Validation manuelle d'un échantillon du jeu d'évaluation, dans le terminal.

Chaque avis est enregistré aussitôt dans data/questions/validation.jsonl : on peut quitter
avec q et reprendre plus tard. Consignes : docs/eval_guidelines.md.
"""

import argparse
import itertools
import json
import random
import textwrap
from collections import defaultdict

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.evalset.verify import EVAL
from juriscope.paths import DATA

VALIDATION = DATA / "questions" / "validation.jsonl"
SEED = 2026


def sample(questions: list[dict], size: int, seed: int) -> list[dict]:
    """Échantillon équilibré entre les types, toujours dans le même ordre."""
    rng = random.Random(seed)
    groups = defaultdict(list)
    for question in questions:
        groups[question["type"]].append(question)
    for group in groups.values():
        rng.shuffle(group)
    mixed = [q for batch in itertools.zip_longest(*groups.values()) for q in batch if q]
    return mixed[:size]


def ask(prompt: str) -> str:
    answer = ""
    while answer not in ("o", "n", "q"):
        answer = input(prompt).strip().lower()
    return answer


def show(question: dict, position: int, total: int, articles: dict) -> None:
    print(f"\n{'=' * 80}\n[{position}/{total}] {question['type']}\n")
    print(f"Question : {question['question']}")
    if not question["relevant"]:
        print(f"Réponse attendue : un refus (question tirée de {question['source']})")
        return
    print(f"Réponse attendue : {question['answer']}")
    for cid in question["relevant"]:
        article = articles[cid]
        text = (
            article["text"] if len(article["text"]) <= 2500 else article["text"][:2500] + " [...]"
        )
        print(f"\n{article['title']}")
        print("\n".join(textwrap.fill(line, width=100) for line in text.splitlines()))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.evalset.annotate")
    parser.add_argument("-n", type=int, default=80, help="taille de l'échantillon")
    args = parser.parse_args()

    articles = {a["cid"]: a for a in load_corpus()}
    done = {row["id"] for row in read_jsonl(VALIDATION)} if VALIDATION.exists() else set()
    todo = [q for q in sample(read_jsonl(EVAL), args.n, SEED) if q["id"] not in done]
    for position, question in enumerate(todo, len(done) + 1):
        show(question, position, args.n, articles)
        clear = ask("\nQuestion claire ? [o/n, q pour quitter] ")
        if clear == "q":
            break
        if question["relevant"]:
            prompt = "Réponse attendue bien dans l'article ? [o/n, q] "
        else:
            prompt = "Question bien hors du Code du travail et des conventions ? [o/n, q] "
        expected = ask(prompt)
        if expected == "q":
            break
        comment = input("Commentaire (Entrée pour passer) : ").strip()
        row = {"id": question["id"], "clear": clear == "o", "expected_ok": expected == "o"}
        with VALIDATION.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row | {"comment": comment}, ensure_ascii=False) + "\n")

    rows = read_jsonl(VALIDATION) if VALIDATION.exists() else []
    clear, correct = sum(r["clear"] for r in rows), sum(r["expected_ok"] for r in rows)
    print(f"\n{len(rows)} questions validées : {clear} claires, {correct} avec la bonne réponse.")


if __name__ == "__main__":
    main()
