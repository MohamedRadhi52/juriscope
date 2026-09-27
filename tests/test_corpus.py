import json

import pytest

from juriscope.corpus import load_corpus
from juriscope.ingest.parse import CONVENTIONS
from juriscope.paths import DATA

pytestmark = pytest.mark.corpus

KNOWN = [
    ("LEGIARTI000006901112", "L1234-1", "faute grave", "Préavis et indemnité compensatrice"),
    ("LEGIARTI000006902466", "L3121-27", "trente-cinq heures par semaine", "Durée légale"),
    ("LEGIARTI000019067614", "L1221-19", "Pour les cadres, de quatre mois", "Période d'essai"),
    ("LEGIARTI000006902640", "L3141-3", "deux jours et demi ouvrables", "Durée du congé"),
    ("KALIARTI000044253063", "3.4", "ne se présument pas", "Titre 3 Conditions d'engagement"),
]


@pytest.fixture(scope="module")
def articles():
    return load_corpus()


@pytest.fixture(scope="module")
def by_cid(articles):
    return {a["cid"]: a for a in articles}


@pytest.mark.parametrize(("cid", "num", "excerpt", "section"), KNOWN)
def test_known_article_is_found_by_its_cid(by_cid, cid, num, excerpt, section):
    article = by_cid[cid]
    assert article["num"] == num
    assert excerpt in article["text"]
    assert any(section in title for title in article["path"])


def test_corpus_has_unique_cids_and_only_articles_in_force(articles):
    assert len({a["cid"] for a in articles}) == len(articles)
    assert all(a["text"] and a["in_force"] for a in articles)
    assert sum(1 for a in articles if not a["idcc"]) > 11_000
    assert {idcc for a in articles for idcc in a["idcc"]} == set(CONVENTIONS)


def test_pilot_questions_point_to_articles_of_the_corpus(articles):
    titles = {a["cid"]: a["title"] for a in articles}
    lines = (DATA / "questions" / "pilote.jsonl").read_text(encoding="utf-8").splitlines()
    for question in map(json.loads, lines):
        assert [titles[cid] for cid in question["relevant"]] == question["refs"]
