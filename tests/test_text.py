from juriscope.retrieve.text import tokenize


def test_elisions_and_stopwords_are_removed():
    assert tokenize("l'employeur") == tokenize("employeur")
    assert tokenize("l\u2019employeur") == tokenize("employeur")
    assert tokenize("jusqu'à la fin") == tokenize("fin")


def test_missing_accents_and_plurals_give_the_same_tokens():
    assert tokenize("période d'essai") == tokenize("periode d'essai")
    assert tokenize("les salariés") == tokenize("salaries") == tokenize("salarié")
    assert tokenize("licenciements") == tokenize("licenciement")


def test_article_references_are_normalized():
    assert tokenize("l'article L. 1234-1") == tokenize("article L1234-1")
    assert "l1234-1" in tokenize("article L1234-1")
    assert tokenize("R.4451-39") == ["r4451-39"]
    assert "3.4" in tokenize("article 3.4 de la convention")


def test_acronyms_are_kept_even_when_they_look_like_stopwords():
    assert tokenize("le CE") == ["ce"]
    assert tokenize("ce contrat") == tokenize("contrat")
    assert tokenize("C.S.E.") == tokenize("CSE") == ["cse"]
