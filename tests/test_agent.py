import json
import sqlite3

from juriscope.agent import evaluate, graph, tools

CODE = {"L1234-1": {"cid": "C1", "title": "Code du travail, art. L1234-1", "text": "Préavis."}}


def test_article_lookup_accepts_the_usual_ways_of_writing_a_number():
    for entree in ("L1234-1", "l'article L. 1234-1", "l1234-1"):
        assert tools.find_article(entree, CODE)["cid"] == "C1"
    assert "erreur" in tools.find_article("L9999-9", CODE)


def test_sql_is_limited_to_one_select_on_a_read_only_database(tmp_path):
    database = tmp_path / "conventions.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE conventions (idcc TEXT, nom TEXT, salaries INTEGER)")
        connection.execute("INSERT INTO conventions VALUES ('1486', 'Syntec', 857061)")
    select = "SELECT nom FROM conventions WHERE salaries > 800000"
    assert tools.query_conventions(select, database) == {"lignes": [{"nom": "Syntec"}]}
    assert "erreur" in tools.query_conventions("DELETE FROM conventions", database)
    assert "erreur" in tools.query_conventions("SELECT * FROM absente", database)
    assert "erreur" in tools.query_conventions("SELECT 1; DELETE FROM conventions", database)
    assert tools.query_conventions("SELECT COUNT(*) AS n FROM conventions", database) == {
        "lignes": [{"n": 1}]
    }


def test_veille_summary(tmp_path):
    report = tmp_path / "rapport.json"
    data = {
        "de": {},
        "vers": {},
        "ajoutes": 2,
        "supprimes": 1,
        "modifies": 1,
        "articles_modifies": [{"cid": "C1", "titre": "Code du travail, art. L1234-1"}],
    }
    report.write_text(json.dumps(data))
    summary = tools.veille_summary(report)
    assert (summary["modifies"], summary["articles_modifies"]) == (
        1,
        ["Code du travail, art. L1234-1"],
    )


def test_agent_uses_tools_until_it_decides_to_finish():
    decisions = iter(
        [
            {"outil": "conventions", "entree": "SELECT nom FROM conventions"},
            {"outil": "article", "entree": "L1234-1"},
            {
                "outil": "fin",
                "refus": False,
                "reponse": "Syntec ; le préavis dépend de l'ancienneté.",
            },
        ]
    )
    tools_ = {
        "conventions": lambda sql: {"lignes": [{"nom": "Syntec"}]},
        "article": lambda number: tools.find_article(number, CODE),
    }
    result = graph.run(graph.build_agent(lambda question, steps: next(decisions), tools_), "Q ?")
    assert result["outils"] == ["conventions", "article"]
    assert result["citations"] == ["C1"]
    assert result["reponse"].startswith("Syntec") and not result["refus"]


def test_agent_stops_after_the_maximum_number_of_tools():
    agent = graph.build_agent(lambda q, steps: {"outil": "veille", "entree": ""}, {"veille": dict})
    result = graph.run(agent, "Q ?")
    assert result["outils"] == ["veille"] * graph.MAX_STEPS
    assert result["reponse"] == ""


def test_success_needs_values_citations_refusal_and_for_the_agent_tools():
    scenario = {
        "contient": ["857061", "metallurgie"],
        "cite": ["C1"],
        "refus": False,
        "outils": ["conventions"],
    }
    result = {
        "reponse": "Syntec : 857 061 salariés ; Métallurgie.",
        "citations": ["C1", "C2"],
        "refus": False,
        "outils": ["conventions"],
    }
    assert evaluate.succeeded(result, scenario, check_tools=True)
    assert not evaluate.succeeded(result | {"outils": []}, scenario, check_tools=True)
    assert evaluate.succeeded(result | {"outils": []}, scenario, check_tools=False)
    assert not evaluate.succeeded(result | {"refus": True}, scenario, check_tools=False)
