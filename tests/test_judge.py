from juriscope.eval import judge
from juriscope.eval.agreement import cohen_kappa, kappa_ci

ARTICLES = {"L1": {"title": "Code du travail, art. L1", "text": "Le congé dure cinq semaines."}}
QUESTION = {"question": "Combien dure le congé ?", "answer": "Cinq semaines.", "relevant": ["L1"]}


def answer(**fields):
    return {
        "refus": False,
        "lisible": True,
        "reponse": "Cinq semaines.",
        "citations": ["L1"],
    } | fields


def never(prompt, model):
    raise AssertionError("le modèle ne doit pas être appelé")


def test_kappa_computed_by_hand():
    # accord observé 3/4 ; hasard 0,5 x 0,25 + 0,5 x 0,75 = 0,5 ; kappa = (0,75 - 0,5) / 0,5
    assert cohen_kappa([1, 1, 0, 0], [1, 0, 0, 0]) == 0.5
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == -1.0


def test_kappa_interval_contains_the_estimate():
    human = [True, False] * 20 + [True] * 10
    model = [True, False] * 20 + [False] * 10
    low, high = kappa_ci(human, model)
    assert low <= cohen_kappa(human, model) <= high


def test_refusals_are_judged_without_the_model():
    outside = QUESTION | {"relevant": []}
    assert judge.verdict(outside, answer(refus=True), ARTICLES, never)["reussi"] is True
    assert judge.verdict(outside, answer(), ARTICLES, never)["reussi"] is False
    assert judge.verdict(QUESTION, answer(refus=True), ARTICLES, never)["reussi"] is False


def test_model_verdict_needs_a_faithful_and_correct_answer():
    def complete(prompt, model):
        assert "Réponse de référence : Cinq semaines." in prompt and model == judge.MODEL
        output = '{"fidele": true, "juste": false, "raison": "incomplet"}'
        return {"output": output, "usage": {"input_tokens": 1, "output_tokens": 1}}

    result = judge.verdict(QUESTION, answer(), ARTICLES, complete)
    assert (result["reussi"], result["fidele"], result["juste"]) == (False, True, False)


def test_agreement_report_and_decision_against_the_threshold():
    judged = [
        {"id": f"q{i}", "relevant": ["L1"], "juge": {"reussi": i % 2 == 0, "usage": {}}}
        for i in range(10)
    ]
    labels = {f"q{i}": i % 2 == 0 for i in range(10)}
    report = judge.agreement(judged, labels)
    assert report["avec_reponse"]["kappa"] == 1.0
    assert report["juge_retenu"]
