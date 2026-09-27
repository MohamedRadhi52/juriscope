"""Vérifie les questions générées et les sépare en développement et test.

Écrit le jeu figé dans data/questions/eval.jsonl et le décompte des rejets par motif dans
results/evalset/verification.json.
"""

import json
import random
import re
from collections import Counter, defaultdict

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.evalset.generate_questions import OUTPUT as GENERATED
from juriscope.evalset.generate_questions import load_css
from juriscope.paths import DATA, ROOT
from juriscope.retrieve.text import fold, tokenize

EVAL = DATA / "questions" / "eval.jsonl"
REPORT = ROOT / "results" / "evalset" / "verification.json"
MAX_COPIED_WORDS = 7
MAX_PARAPHRASE_OVERLAP = 0.4
DEV_SHARE = 0.6
SEED = 2026


def words(text: str) -> list[str]:
    return re.findall(r"\w+", fold(text).lower())


def quoted(extract: str, text: str) -> bool:
    """Vrai si l'extrait figure dans le texte ; une coupure [...] sépare des morceaux."""
    parts = [words(part) for part in re.split(r"\[\.\.\.\]|\(\.\.\.\)|\.\.\.|…", extract)]
    padded = f" {' '.join(words(text))} "
    return sum(map(len, parts)) >= 3 and all(f" {' '.join(p)} " in padded for p in parts if p)


def as_question(text: str) -> str:
    """Question sans espaces superflus, terminée par un point d'interrogation plutôt qu'un point."""
    text = text.strip()
    return text[:-1].rstrip() + " ?" if text.endswith(".") else text


def copied_words(question: str, text: str) -> int:
    """Longueur de la plus longue suite de mots de la question reprise telle quelle du texte."""
    q, padded = words(question), f" {' '.join(words(text))} "
    best = 0
    for start in range(len(q)):
        end = start + best + 1
        while end <= len(q) and f" {' '.join(q[start:end])} " in padded:
            best, end = end - start, end + 1
    return best


def overlap(question: str, text: str) -> float:
    """Part des mots pleins de la question, racinisés, qui figurent dans le texte."""
    tokens = set(tokenize(question))
    return len(tokens & set(tokenize(text))) / len(tokens) if tokens else 1.0


def parse_output(raw: str) -> dict | None:
    """Objet JSON de la réponse, même entouré de texte ou d'un bloc de code."""
    start, end = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def rejection(output: dict, kind: str, texts: list[str]) -> str | None:
    """Motif de rejet d'une question générée, ou None si elle passe les vérifications."""
    question = as_question(output.get("question", ""))
    if not question:
        return "article sans question utile"
    if not question.endswith("?") or not 5 <= len(words(question)) <= 45:
        return "forme de la question"
    extracts = output.get("extraits") or [output.get("extrait", "")]
    if len(extracts) != len(texts) or not all(
        quoted(e, t) for e, t in zip(extracts, texts, strict=True)
    ):
        return "extrait absent de l'article"
    if max(copied_words(question, t) for t in texts) >= MAX_COPIED_WORDS:
        return "question recopiée du texte"
    if kind == "paraphrase" and overlap(question, texts[0]) > MAX_PARAPHRASE_OVERLAP:
        return "paraphrase trop proche du texte"
    return None


def split(questions: list[dict], seed: int) -> None:
    """Répartit chaque type entre dev et test, dans les mêmes proportions."""
    rng = random.Random(seed)
    by_type = defaultdict(list)
    for question in questions:
        by_type[question["type"]].append(question)
    for group in by_type.values():
        rng.shuffle(group)
        cut = round(DEV_SHARE * len(group))
        for i, question in enumerate(group):
            question["split"] = "dev" if i < cut else "test"


def main() -> None:
    articles = {a["cid"]: a for a in load_corpus()} | {a["cid"]: a for a in load_css()}
    generated = read_jsonl(GENERATED)
    kept, rejected, seen = [], defaultdict(list), set()
    for item in generated:
        output = parse_output(item["output"])
        texts = [articles[source["cid"]]["text"] for source in item["sources"]]
        reason = (
            "réponse JSON invalide" if output is None else rejection(output, item["type"], texts)
        )
        question = as_question(output.get("question", "")) if output else ""
        key = " ".join(words(question))
        if reason is None and key in seen:
            reason = "question en double"
        if reason:
            rejected[reason].append(item["id"])
            continue
        seen.add(key)
        row = {
            "id": item["id"],
            "type": item["type"],
            "question": question,
            "answer": output.get("reponse", ""),
            "relevant": item["relevant"],
            "refs": [s["title"] for s in item["sources"] if s["cid"] in item["relevant"]],
        }
        if not item["relevant"]:
            row["source"] = item["sources"][0]["title"]
        kept.append(row)
    split(kept, SEED)

    with EVAL.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    types = Counter(item["type"] for item in generated)
    report = {
        "modeles": Counter(item["model"] for item in generated),
        "jetons_entree": sum(item["usage"]["input_tokens"] for item in generated),
        "jetons_sortie": sum(item["usage"]["output_tokens"] for item in generated),
        "questions_generees": len(generated),
        "questions_gardees": len(kept),
        "par_type": {
            kind: {
                "generees": n,
                "gardees": sum(1 for q in kept if q["type"] == kind),
                "dev": sum(1 for q in kept if q["type"] == kind and q["split"] == "dev"),
            }
            for kind, n in types.items()
        },
        "rejets": {reason: len(ids) for reason, ids in rejected.items()},
        "rejets_par_id": rejected,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(kept)} questions gardées sur {len(generated)} ; rejets : {report['rejets']}")


if __name__ == "__main__":
    main()
