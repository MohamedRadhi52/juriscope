import io
import json

from juriscope.generate import pipeline
from juriscope.ingest import diff, npm


def article(cid, text, num="L1", idcc=()):
    return {
        "cid": cid,
        "text": text,
        "num": num,
        "title": f"Code du travail, art. {num}",
        "idcc": list(idcc),
    }


OLD = [article("A", "Préavis d'un mois."), article("B", "Texte stable."), article("C", "Abrogé.")]
NEW = [
    article("A", "Préavis de deux mois.", "L1234-1"),
    article("B", "Texte stable."),
    article("D", "Nouvel article."),
]


def test_diff_uses_the_common_identifier():
    assert diff.diff(OLD, NEW) == {"ajoutes": ["D"], "supprimes": ["C"], "modifies": ["A"]}


def test_questions_touched_by_a_modified_or_removed_article():
    questions = [
        {"id": "q1", "relevant": ["A"]},
        {"id": "q2", "relevant": ["B"]},
        {"id": "q3", "relevant": ["C", "B"]},
        {"id": "q4", "relevant": []},
    ]
    assert diff.affected(diff.diff(OLD, NEW), questions) == ["q1", "q3"]


def test_temporal_questions_ask_for_the_wording_in_force():
    changes = diff.diff(OLD, NEW)
    [question] = diff.temporal_questions(changes, {a["cid"]: a for a in NEW})
    assert question["question"] == "Que prévoit aujourd'hui l'article L1234-1 du Code du travail ?"
    assert (question["type"], question["relevant"]) == ("temporelle", ["A"])


def test_release_reads_the_version_and_its_integrity(monkeypatch):
    meta = {"version": "2.552.0", "dist": {"integrity": "sha512-abc"}}
    urls = []

    def fake_urlopen(url, timeout):
        urls.append(url)
        return io.BytesIO(json.dumps(meta).encode())

    monkeypatch.setattr(npm, "urlopen", fake_urlopen)
    assert npm.release("@socialgouv/legi-data", "2.552.0") == {
        "version": "2.552.0",
        "integrity": "sha512-abc",
    }
    assert urls == ["https://registry.npmjs.org/@socialgouv/legi-data/2.552.0"]


def test_answer_flags_cited_articles_modified_since_the_last_version():
    class Fixed:
        def search(self, query, k):
            return ["A", "B"]

    def complete(prompt, model):
        return {
            "output": '{"refus": false, "reponse": "R", "citations": [1, 2]}',
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }

    articles = {a["cid"]: a | {"title": "T"} for a in NEW}
    result = pipeline.answer(
        "Q ?", Fixed(), articles, complete, "claude-haiku-4-5-20251001", changed=frozenset({"A"})
    )
    assert result["articles_modifies"] == ["A"]
