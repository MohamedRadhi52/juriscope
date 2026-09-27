from datetime import UTC, datetime

from juriscope.ingest import parse

NO_END = 32472144000000  # 1er janvier 2999, "sans date de fin" dans LEGI


def ms(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)


def section(title: str, *children: dict) -> dict:
    return {"type": "section", "data": {"title": title}, "children": list(children)}


def legi_article(id_, num, html, state="VIGUEUR", start="2008-05-01", end=None):
    data = {"id": id_, "cid": "C" + id_, "num": num, "texteHtml": html, "etat": state}
    data |= {"dateDebut": ms(start), "dateFin": ms(end) if end else NO_END}
    return {"type": "article", "data": data}


def kali_article(id_, content, num=None, heading=None, state="VIGUEUR_ETEN"):
    data = {"id": id_, "cid": id_, "content": content, "etat": state}
    if num:
        data["num"] = num
    if heading:
        data["surtitre"] = heading
    return {"type": "article", "data": data}


CODE = {
    "type": "code",
    "data": {"title": "Code du travail", "dateDebutVersion": "2026-09-01"},
    "children": [
        section(
            "Partie législative  ",
            section(
                "Section 4 : Période d'essai.\r\n\r\n",
                legi_article("A1", "L1221-19", "<p>Durée maximale :</p><p>1° deux mois&nbsp;;</p>"),
                legi_article(
                    "A2", "L1142-11", "<p>Texte.</p>", "ABROGE_DIFF", "2026-03-01", "2029-03-01"
                ),
                legi_article(
                    "A3", "R4451-39", "<p>Rédaction future.</p>", "VIGUEUR_DIFF", "2027-07-01"
                ),
            ),
        )
    ],
}

CONVENTION = {
    "type": "convention collective",
    "data": {"shortTitle": "Bureaux d'études"},
    "children": [
        section(
            "Texte de base : Convention collective nationale du 15 décembre 1987",
            section(
                "Titre 3 Conditions d'engagement",
                kali_article("K1", "<p>L'essai ne se présume pas.</p>", "3.4", "Période d'essai"),
                kali_article("K2", "", "3.5"),
            ),
        ),
        section(
            "Textes Attachés",
            section(
                "Accord du 7 octobre 2015 relatif à la complémentaire santé",
                kali_article("K3", "<p>Accord à durée indéterminée.</p>", heading="Durée"),
                kali_article("K5", "<p>Les signataires conviennent de ce qui suit.</p>"),
            ),
        ),
        section(
            "Textes Salaires", section("Avenant salaires", kali_article("K4", "<p>Grille</p>"))
        ),
    ],
}


def test_html_to_text_keeps_one_paragraph_per_line():
    html = "<p>Premier alinéa&nbsp;:</p><p>1° deux mois ;<br/>2° <b>trois</b> mois.</p>"
    assert parse.html_to_text(html) == "Premier alinéa :\n1° deux mois ;\n2° trois mois."


def test_legi_articles_have_path_dates_and_validity():
    first, deferred, future = parse.legi_articles(CODE)
    assert first["title"] == "Code du travail, art. L1221-19"
    assert first["cid"] == "CA1"
    assert first["path"] == [
        "Code du travail",
        "Partie législative",
        "Section 4 : Période d'essai.",
    ]
    assert first["text"] == "Durée maximale :\n1° deux mois ;"
    assert (first["start"], first["end"], first["in_force"]) == ("2008-05-01", None, True)
    assert (deferred["end"], deferred["in_force"]) == ("2029-03-01", True)
    assert not future["in_force"]


def test_kali_articles_skip_salaries_and_name_the_text():
    articles = list(parse.kali_articles(CONVENTION, "1486"))
    assert [a["id"] for a in articles] == ["K1", "K2", "K3", "K5"]
    base, _, attached, untitled = articles
    assert base["title"] == "Syntec (IDCC 1486), texte de base, art. 3.4 : Période d'essai"
    assert base["path"][0] == "Convention collective Syntec (IDCC 1486) : Bureaux d'études"
    assert attached["title"] == (
        "Syntec (IDCC 1486), Accord du 7 octobre 2015 relatif à la complémentaire santé, Durée"
    )
    assert untitled["title"] == (
        "Syntec (IDCC 1486), Accord du 7 octobre 2015 relatif à la complémentaire santé"
    )
    assert all(a["idcc"] == ["1486"] and a["in_force"] for a in articles)


def test_article_shared_by_two_conventions_is_kept_once():
    articles = [
        {"id": "K1", "idcc": ["2120"]},
        {"id": "K2", "idcc": ["2120"]},
        {"id": "K1", "idcc": ["1672"]},
    ]
    merged = parse.merge_shared(articles)
    assert [(a["id"], a["idcc"]) for a in merged] == [("K1", ["2120", "1672"]), ("K2", ["2120"])]
