from juriscope.retrieve.rerank import Rerank, parse_order

ARTICLES = {c: {"title": f"Titre {c}", "text": f"Texte de l'article {c}."} for c in "ABC"}


class Fixed:
    def search(self, query, k):
        return ["A", "B", "C"][:k]


def reranker(output):
    prompts = []

    def complete(prompt, model):
        prompts.append(prompt)
        return {"output": output, "usage": {"input_tokens": 100, "output_tokens": 10}}

    return Rerank(Fixed(), ARTICLES, complete, "claude-haiku-4-5-20251001"), prompts


def test_parse_order_keeps_valid_distinct_numbers():
    assert parse_order('{"ordre": [3, 1, 9, 1, "2"]}', n=3) == [3, 1]
    assert parse_order("illisible", n=3) == []


def test_model_order_first_then_the_other_candidates():
    rerank, prompts = reranker('```json\n{"ordre": [3, 1]}\n```')
    assert rerank.search("Question ?", k=3) == ["C", "A", "B"]
    assert "[2] Titre B\nTexte de l'article B." in prompts[0]
    assert rerank.cost() == (100 * 1.0 + 10 * 5.0) / 1e6


def test_unreadable_answer_keeps_the_initial_order():
    rerank, _ = reranker("Je ne sais pas.")
    assert rerank.search("Question ?", k=3) == ["A", "B", "C"]
    assert rerank.unparsed == 1
