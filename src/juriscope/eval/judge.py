"""Juge LLM des réponses citées, validé contre les étiquettes humaines.

Le juge suit la grille donnée aux annotateurs (docs/eval_guidelines.md). Un refus se juge
sans modèle : il est correct pour une question hors corpus et faux sinon.
"""

import json
from pathlib import Path

import numpy as np

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.eval.agreement import cohen_kappa, kappa_ci
from juriscope.evalset.annotate import VALIDATION
from juriscope.evalset.verify import EVAL
from juriscope.generate.providers import anthropic_complete, cost, extract_json
from juriscope.generate.run_generation import OUTPUT, summarize

MODEL = "claude-sonnet-5-5"
THRESHOLD = 0.6
PROMPT = """Tu évalues la réponse d'un assistant de droit du travail français.

Question : {question}

Réponse de référence : {reference}

Article de référence :
{expected}

Réponse de l'assistant : {answer}

Articles cités par l'assistant :
{cited}

Grille :
- fidèle : chaque affirmation de la réponse est appuyée par les articles cités, sans règle \
inventée ni article qui ne dit pas ce qu'elle affirme ;
- juste : la réponse répond à la question sans erreur, en accord avec la réponse et l'article \
de référence.

Réponds uniquement en JSON : {{"fidele": true, "juste": true, "raison": "une phrase"}}"""


def render(cids: list[str], articles: dict) -> str:
    return "\n\n".join(f"{articles[c]['title']}\n{articles[c]['text'][:2000]}" for c in cids)


def verdict(question: dict, answer: dict, articles: dict, complete) -> dict:
    """Verdict du juge : réussi, fidèle, juste, raison, et l'usage en jetons s'il a servi."""
    if not question["relevant"]:
        return {
            "reussi": answer["refus"],
            "raison": "question hors corpus : seul un refus est juste",
        }
    if answer["refus"] or not answer["lisible"]:
        return {"reussi": False, "raison": "refus ou réponse illisible alors qu'une réponse existe"}
    prompt = PROMPT.format(
        question=question["question"],
        reference=question["answer"],
        expected=render(question["relevant"], articles),
        answer=answer["reponse"],
        cited=render(answer["citations"], articles) or "aucun",
    )
    result = complete(prompt, MODEL)
    grade = extract_json(result["output"]) or {}
    fidele, juste = grade.get("fidele") is True, grade.get("juste") is True
    return {
        "reussi": fidele and juste,
        "fidele": fidele,
        "juste": juste,
        "raison": grade.get("raison", "réponse du juge illisible"),
        "usage": result["usage"],
    }


def judge_file(path: Path, questions: dict, articles: dict, complete) -> list[dict]:
    """Juge chaque réponse d'un fichier ; renvoie les réponses complétées du verdict."""
    rows = read_jsonl(path)
    return [row | {"juge": verdict(questions[row["id"]], row, articles, complete)} for row in rows]


def agreement(judged: list[dict], labels: dict) -> dict:
    """Kappa entre juge et humain, sur toutes les questions puis sur celles qui ont une réponse."""
    report = {"seuil": THRESHOLD}
    subsets = {
        "toutes": judged,
        "avec_reponse": [r for r in judged if r["relevant"]],
        "jugees_par_le_modele": [r for r in judged if "usage" in r["juge"]],
    }
    for name, rows in subsets.items():
        human = [labels[r["id"]] for r in rows]
        model = [r["juge"]["reussi"] for r in rows]
        report[name] = {
            "questions": len(rows),
            "accord_brut": float(np.mean(np.equal(human, model))),
            "kappa": cohen_kappa(human, model),
            "ic95": kappa_ci(human, model),
            "humain_oui_juge_non": sum(h and not m for h, m in zip(human, model, strict=True)),
            "humain_non_juge_oui": sum(m and not h for h, m in zip(human, model, strict=True)),
        }
    report["juge_retenu"] = report["avec_reponse"]["kappa"] >= THRESHOLD
    return report


def main() -> None:
    articles = {a["cid"]: a for a in load_corpus()}
    questions = {q["id"]: q for q in read_jsonl(EVAL)}
    # Sonnet 5.5 refuse le réglage de température : le juge garde celui du modèle
    complete = anthropic_complete
    labels = {row["id"]: row["answer_ok"] for row in read_jsonl(VALIDATION)}

    sample = judge_file(OUTPUT / "answers.jsonl", questions, articles, complete)
    report = agreement([r for r in sample if r["id"] in labels], labels)

    dev = judge_file(OUTPUT / "dev_answers.jsonl", questions, articles, complete)
    inside = [r for r in dev if r["relevant"]]
    judged = [r for r in inside if "usage" in r["juge"]]
    usages = [r["juge"]["usage"] for r in sample + dev if "usage" in r["juge"]]
    summary = summarize(dev) | {
        "reussite": float(np.mean([r["juge"]["reussi"] for r in dev])),
        "reussite_avec_reponse": float(np.mean([r["juge"]["reussi"] for r in inside])),
        "fidelite": float(np.mean([r["juge"]["fidele"] for r in judged])),
        "justesse": float(np.mean([r["juge"]["juste"] for r in judged])),
        "cout_du_juge": cost(usages, MODEL),
    }
    out = OUTPUT / "juge"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("echantillon", sample), ("dev", dev)):
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (out / "accord.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (out / "dev_resume.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"accord": report["avec_reponse"], "dev": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
