import json

from juriscope.corpus import read_jsonl
from juriscope.evalset import annotate, generate_questions, verify

LONG = "Le salarié bénéficie de ce droit dans les conditions prévues par la loi. " * 4
PART_1 = ["Code du travail", "Partie législative", "Première partie : Relations individuelles"]
PART_1_R = ["Code du travail", "Partie réglementaire", "Première partie : Relations individuelles"]
PART_2 = ["Code du travail", "Partie législative", "Deuxième partie : Relations collectives"]
CSS = ["Code de la sécurité sociale", "Partie législative", "Livre III : Assurances sociales"]
COUNTS = dict.fromkeys(generate_questions.COUNTS, 1)


def article(cid, path, idcc=(), num="", text=LONG):
    return {
        "cid": cid,
        "title": f"Titre {cid}",
        "path": path,
        "idcc": list(idcc),
        "num": num,
        "text": f"{text} ({cid})",
    }


CORPUS = (
    [article(f"L{i}", [*PART_1, "Section 1"], num=f"L1001-{i}") for i in range(12)]
    + [article(f"R{i}", [*PART_1_R, "Section 1"], num=f"R1001-{i}") for i in range(3)]
    + [article(f"M{i}", [*PART_2, "Section 2"], num=f"L2001-{i}") for i in range(6)]
    + [article(f"K{i}", ["Convention Syntec"], idcc=["1486"]) for i in range(2)]
    + [
        article(
            "K9",
            ["Convention Syntec"],
            idcc=["1486"],
            text=LONG + "Voir les articles L. 1001-1, L. 1001-2 et L. 1001-3.",
        )
    ]
)
CSS_ARTICLES = [article(f"S{i}", [*CSS, "Titre V : Assurance vieillesse"]) for i in range(3)]


def test_tasks_cover_every_type_without_reusing_an_article():
    tasks = generate_questions.build_tasks(CORPUS, CSS_ARTICLES, COUNTS, seed=1)
    kinds = [t["type"] for t in tasks]
    assert set(kinds) == {
        "factuelle",
        "paraphrase",
        "multi-articles",
        "convention contre code",
        "hors corpus",
    }
    sources = [s["cid"] for t in tasks for s in t["sources"]]
    assert len(sources) == len(set(sources))
    outside = next(t for t in tasks if t["type"] == "hors corpus")
    assert outside["relevant"] == [] and "sécurité sociale" in outside["prompt"]
    comparison = next(t for t in tasks if t["type"] == "convention contre code")
    convention, code = (s["cid"] for s in comparison["sources"])
    assert convention == "K9" and code in {"L1", "L2", "L3"}
    assert "nom courant : Syntec" in comparison["prompt"]
    assert tasks == generate_questions.build_tasks(CORPUS, CSS_ARTICLES, COUNTS, seed=1)


def test_generation_resumes_without_rewriting(tmp_path):
    tasks = [
        {"id": f"q000{i}", "type": "factuelle", "sources": [], "relevant": [], "prompt": "?"}
        for i in range(1, 4)
    ]
    output = tmp_path / "generated.jsonl"

    def llm(prompt, model, seed):
        return {"model": model, "output": "{}", "usage": {"total_tokens": 1}}

    assert generate_questions.generate(tasks[:2], output, llm) == 2
    assert generate_questions.generate(tasks, output, llm) == 1
    assert generate_questions.generate(tasks, output, llm) == 0
    rows = read_jsonl(output)
    assert [r["id"] for r in rows] == ["q0001", "q0002", "q0003"]
    assert "prompt" not in rows[0]


def test_copied_words_and_overlap():
    text = "La durée légale du travail effectif est fixée à trente-cinq heures par semaine."
    assert verify.copied_words("Quelle est la durée légale du travail ?", text) == 5
    assert verify.copied_words("Combien d'heures par semaine ?", text) == 3
    assert verify.overlap("Combien d'heures par semaine pour un temps plein ?", text) < 0.5


def test_rejection_reasons():
    text = "La durée légale du travail effectif est fixée à trente-cinq heures par semaine."
    good = {
        "question": "Combien d'heures dure une semaine de travail à temps plein ?",
        "extrait": "fixée à trente-cinq heures",
    }
    assert verify.rejection(good, "factuelle", [text]) is None
    assert verify.rejection({"question": ""}, "factuelle", [text]) == "article sans question utile"
    invented = good | {"extrait": "trente-neuf heures par semaine"}
    assert verify.rejection(invented, "factuelle", [text]) == "extrait absent de l'article"
    copied = good | {"question": "La durée légale du travail effectif est fixée à combien ?"}
    assert verify.rejection(copied, "factuelle", [text]) == "question recopiée du texte"
    close = good | {"question": "Quelle durée légale de travail effectif par semaine ?"}
    assert verify.rejection(close, "paraphrase", [text]) == "paraphrase trop proche du texte"


def test_split_keeps_the_same_share_in_each_type():
    questions = [{"type": "a"} for _ in range(10)] + [{"type": "b"} for _ in range(5)]
    verify.split(questions, seed=0)
    dev = [q["type"] for q in questions if q["split"] == "dev"]
    assert (dev.count("a"), dev.count("b")) == (6, 3)


def test_annotation_can_stop_and_resume(tmp_path, monkeypatch):
    questions = [
        {"id": "q1", "type": "factuelle", "question": "Q1 ?", "answer": "R1", "relevant": ["L0"]},
        {
            "id": "q2",
            "type": "hors corpus",
            "question": "Q2 ?",
            "answer": "",
            "relevant": [],
            "source": "Code de la sécurité sociale, art. L1",
        },
    ]
    eval_file, validation = tmp_path / "eval.jsonl", tmp_path / "validation.jsonl"
    eval_file.write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
    monkeypatch.setattr(annotate, "EVAL", eval_file)
    monkeypatch.setattr(annotate, "VALIDATION", validation)
    monkeypatch.setattr(annotate, "load_corpus", lambda: CORPUS)
    monkeypatch.setattr("sys.argv", ["annotate", "-n", "2"])

    answers = iter(["o", "n", "RAS", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    annotate.main()
    answers = iter(["x", "o", "o", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    annotate.main()

    rows = read_jsonl(validation)
    assert {r["id"] for r in rows} == {"q1", "q2"}
    assert next(r for r in rows if r["id"] == "q1") == {
        "id": "q1",
        "clear": True,
        "expected_ok": False,
        "comment": "RAS",
    }
