from juriscope.generate import pipeline, run_generation

ARTICLES = {c: {"title": f"Titre {c}", "text": f"Texte {c}."} for c in "ABC"}


class Fixed:
    def search(self, query, k):
        return ["A", "B", "C"][:k]


def complete_with(output):
    prompts = []

    def complete(prompt, model):
        prompts.append(prompt)
        return {"output": output, "usage": {"input_tokens": 1000, "output_tokens": 100}}

    return complete, prompts


def test_answer_maps_citations_and_counts_those_outside_the_context():
    complete, prompts = complete_with('{"refus": false, "reponse": "R", "citations": [2, 7]}')
    result = pipeline.answer("Q ?", Fixed(), ARTICLES, complete, "claude-haiku-4-5-20251001", k=3)
    assert "[3] Titre C\nTexte C." in prompts[0]
    assert (result["citations"], result["citations_hors_contexte"]) == (["B"], 1)
    assert result["cout"] == (1000 * 1.0 + 100 * 5.0) / 1e6
    assert set(result["latence_ms"]) == {"recherche", "generation", "total"}


def test_refusal_and_unreadable_output():
    complete, _ = complete_with('```json\n{"refus": true, "reponse": "", "citations": []}\n```')
    assert pipeline.answer("Q ?", Fixed(), ARTICLES, complete, "claude-haiku-4-5-20251001")["refus"]
    complete, _ = complete_with("Désolé.")
    result = pipeline.answer("Q ?", Fixed(), ARTICLES, complete, "claude-haiku-4-5-20251001")
    assert (result["lisible"], result["refus"], result["citations"]) == (False, False, [])


def test_summary_of_the_automatic_measures():
    def row(relevant, refus, citations, total_ms):
        return {
            "relevant": relevant,
            "refus": refus,
            "citations": citations,
            "lisible": True,
            "citations_hors_contexte": 0,
            "latence_ms": {"total": total_ms},
            "cout": 0.002,
        }

    rows = [row(["A"], False, ["A"], 1000), row(["B"], True, [], 2000), row([], True, [], 500)]
    summary = run_generation.summarize(rows)
    assert (summary["refus_corrects"], summary["refus_a_tort"]) == (1.0, 0.5)
    assert (summary["article_attendu_cite"], summary["citations_dans_le_contexte"]) == (0.5, 1.0)
    assert summary["cout_1000_requetes"] == 2.0
