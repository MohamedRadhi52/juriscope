import numpy as np

from juriscope.eval.metrics import paired_gain_ci
from juriscope.retrieve import embed, finetune

LONG = "Le salarié bénéficie de ce droit dans les conditions prévues par la loi. " * 4


def article(cid):
    return {"cid": cid, "title": f"Titre {cid}", "path": ["Code du travail", "S"], "text": LONG}


def test_training_articles_never_come_from_the_evaluation_set():
    corpus = [article(f"A{i}") for i in range(20)]
    chosen = finetune.training_articles(corpus, {"A0", "A1", "A2"}, n=10, seed=0)
    assert len(chosen) == 10 and not {"A0", "A1", "A2"} & {a["cid"] for a in chosen}


def test_questions_are_read_from_the_json_answer():
    def complete(prompt, model):
        return {"output": '```json\n{"questions": ["Q1 ?", "", "Q2 ?"]}\n```', "usage": {}}

    assert finetune.write_questions(article("A"), complete) == ["Q1 ?", "Q2 ?"]
    pairs = finetune.generate_pairs([article("A"), article("B")], write=lambda a: [f"{a['cid']} ?"])
    assert pairs == [{"cid": "A", "question": "A ?"}, {"cid": "B", "question": "B ?"}]


def test_hard_negatives_skip_the_top_ranks_the_positive_and_excluded_articles():
    ranking = [f"D{i}" for i in range(50)]
    pairs = [{"cid": "D12", "question": "Q ?"}]
    [triplet] = finetune.mine_negatives(pairs, lambda q, k: ranking[:k], {"D11"}, seed=0)
    assert triplet["negative"] in ranking[10:]
    assert triplet["negative"] not in {"D11", "D12"}


def test_shards_are_merged_into_one_file(tmp_path, monkeypatch):
    monkeypatch.setattr(embed, "INDEX", tmp_path)
    for shard, keys in enumerate((["A", "C"], ["B"])):
        embed.save(tmp_path / f"ft-passages-{shard}.npz", keys, np.ones((len(keys), 3)))
    embed.merge("ft-", shards=2)
    merged = np.load(tmp_path / "ft-passages.npz")
    assert merged["keys"].tolist() == ["A", "C", "B"]
    assert merged["vectors"].shape == (3, 3)


def test_paired_gain_interval():
    assert paired_gain_ci([0, 1, 0, 1], [0, 1, 0, 1]) == (0.0, 0.0, 0.0)
    gain, low, high = paired_gain_ci([0, 0, 0, 0], [1, 1, 1, 1])
    assert gain == low == high == 1.0
