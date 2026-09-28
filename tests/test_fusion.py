from juriscope.retrieve.fusion import Hybrid, rrf


def test_rrf_computed_by_hand():
    # a : 1/61 ; b : 1/62 + 1/61 ; c : 1/63 + 1/62 ; d : 1/63
    assert rrf([["a", "b", "c"], ["b", "c", "d"]]) == ["b", "c", "a", "d"]


class Fixed:
    def __init__(self, ranking):
        self.ranking = ranking

    def search(self, query, k):
        return self.ranking[:k]


def test_hybrid_fuses_the_rankings_of_its_retrievers():
    # a et c : 1/61 + 1/63, à égalité devant b : 2/62 ; l'égalité garde l'ordre d'arrivée
    hybrid = Hybrid([Fixed(["a", "b", "c"]), Fixed(["c", "b", "a"])], depth=3)
    assert hybrid.search("question", k=3) == ["a", "c", "b"]
