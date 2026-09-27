import math

import pytest

from juriscope.eval.metrics import bootstrap_ci, ndcg_at_k, recall_at_k, reciprocal_rank

RANKED = ["a", "b", "c", "d", "e"]
RELEVANT = {"b", "d"}


def test_recall_at_k():
    assert recall_at_k(RANKED, RELEVANT, 1) == 0
    assert recall_at_k(RANKED, RELEVANT, 2) == 0.5
    assert recall_at_k(RANKED, RELEVANT, 5) == 1


def test_reciprocal_rank_uses_the_first_relevant_article():
    assert reciprocal_rank(RANKED, RELEVANT, 10) == 0.5
    assert reciprocal_rank(RANKED, RELEVANT, 1) == 0
    assert reciprocal_rank(RANKED, {"z"}, 10) == 0


def test_ndcg_computed_by_hand():
    # articles pertinents aux rangs 2 et 4, rangs 1 et 2 dans le classement idéal
    expected = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(RANKED, RELEVANT, 5) == pytest.approx(expected)
    assert expected == pytest.approx(0.6509, abs=1e-4)
    assert ndcg_at_k(["b", "d", "a"], RELEVANT, 10) == pytest.approx(1)


def test_bootstrap_interval_contains_the_mean_and_is_reproducible():
    values = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1]
    low, high = bootstrap_ci(values)
    assert 0 <= low < 0.7 < high <= 1
    assert bootstrap_ci(values) == (low, high)
    assert bootstrap_ci([0.5] * 20) == (0.5, 0.5)
