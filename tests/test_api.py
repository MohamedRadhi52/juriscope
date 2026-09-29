from fastapi.testclient import TestClient

from juriscope.api import create_app, legifrance_url
from juriscope.eval.gate import failures, sample

ARTICLES = {
    "C1": {"id": "LEGIARTI000033020376", "title": "Code du travail, art. L3121-27"},
    "K1": {"id": "KALIARTI000047513825", "title": "Syntec (IDCC 1486), texte de base, art. 3.4"},
}


def respond(question):
    return {
        "reponse": "Trente-cinq heures.",
        "refus": False,
        "citations": ["C1", "K1"],
        "articles_modifies": [],
        "latence_ms": {"total": 1234.5},
        "cout": 0.004,
    }


def test_ask_returns_the_answer_with_legifrance_links():
    client = TestClient(create_app(respond, ARTICLES))
    body = client.post("/ask", json={"question": "Quelle est la durée légale du travail ?"}).json()
    assert body["reponse"] == "Trente-cinq heures." and body["latence_ms"] == 1234
    assert [c["url"] for c in body["citations"]] == [
        "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033020376",
        "https://www.legifrance.gouv.fr/conv_coll/article/KALIARTI000047513825",
    ]


def test_ask_rejects_a_request_without_question():
    client = TestClient(create_app(respond, ARTICLES))
    assert client.post("/ask", json={}).status_code == 422


def test_legifrance_url_uses_the_version_in_force():
    assert legifrance_url(ARTICLES["C1"]).endswith("/LEGIARTI000033020376")


def test_gate_fails_below_any_threshold():
    measures = {
        "rappel@10": 0.70,
        "reponses_lisibles": 1.0,
        "citations_dans_le_contexte": 0.95,
        "article_attendu_cite": 0.6,
        "refus_corrects": 1.0,
    }
    assert failures(measures) == []
    assert failures(measures | {"rappel@10": 0.61}) == ["rappel@10"]


def test_gate_sample_is_fixed_and_includes_out_of_corpus_questions():
    questions = [
        {"id": f"q{i}", "split": "dev", "relevant": ["A"] if i % 5 else []} for i in range(40)
    ]
    chosen = sample(questions)
    assert len(chosen) == 12 and sum(not q["relevant"] for q in chosen) == 2
    assert chosen == sample(questions)
