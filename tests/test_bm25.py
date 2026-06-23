from juriscope.retrieve.bm25 import BM25

ARTICLES = [
    {
        "cid": "A",
        "path": ["Code du travail", "Section 4 : Période d'essai"],
        "title": "Code du travail, art. L1221-19",
        "text": "Le contrat de travail à durée indéterminée peut comporter une période d'essai.",
    },
    {
        "cid": "B",
        "path": ["Code du travail", "Section 2 : Durée du congé"],
        "title": "Code du travail, art. L3141-3",
        "text": "Le salarié a droit à un congé de deux jours et demi ouvrables par mois.",
    },
    {
        "cid": "C",
        "path": ["Convention collective Syntec (IDCC 1486) : Bureaux d'études techniques"],
        "title": "Syntec (IDCC 1486), texte de base, art. 4.2 : Durée du préavis",
        "text": "La durée varie selon l'ancienneté et la catégorie professionnelle.",
    },
]


def test_search_ranks_the_matching_article_first():
    bm25 = BM25(ARTICLES)
    assert bm25.search("combien de jours de congé par mois ?", k=1) == ["B"]
    assert bm25.search("periode d'essai", k=3)[0] == "A"


def test_path_and_title_are_searchable():
    # "Syntec" et "préavis" n'apparaissent que dans le chemin et le titre de l'article
    assert BM25(ARTICLES).search("preavis Syntec", k=1) == ["C"]
