from juriscope.retrieve.references import References, cited_numbers

ARTICLES = [
    {"cid": "C1", "num": "L1234-1", "idcc": []},
    {"cid": "C2", "num": "L3142-89", "idcc": []},
    {"cid": "K1", "num": "4.2", "idcc": ["1486"]},
]


class Fixed:
    def search(self, query, k):
        return ["X", "C1", "Y"][:k]


def test_article_numbers_are_normalized():
    assert cited_numbers("l'article L. 1234-1 et R4451-39") == ["L1234-1", "R4451-39"]
    assert cited_numbers("article 4.2 de la convention") == []


def test_cited_article_goes_first_without_duplicate():
    references = References(Fixed(), ARTICLES)
    assert references.search("Que dit l'article L1234-1 ?", k=3) == ["C1", "X", "Y"]
    assert references.search("Et L3142-89 ?", k=2) == ["C2", "X"]
    assert references.search("Sans numéro ?", k=3) == ["X", "C1", "Y"]
