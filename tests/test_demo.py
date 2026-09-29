import json

from juriscope import demo


def test_label_in_the_margin():
    assert demo.label({"idcc": [], "num": "L3141-3"}) == "L3141-3"
    assert demo.label({"idcc": ["1486"], "num": "4.2"}) == "Syntec, art. 4.2"
    assert demo.label({"idcc": ["2120"], "num": ""}) == "Banque"


def test_markdown_bold_is_removed():
    assert demo.plain("Le **préavis** dure __un mois__.") == "Le préavis dure un mois."


def test_site_embeds_the_answers_safely(tmp_path, monkeypatch):
    answers = [
        {
            "groupe": "Code du travail",
            "question": "Q ?",
            "refus": False,
            "reponse": "Texte avec </script> dedans.",
            "citations": [],
            "latence_ms": 1200,
            "cout": 0.008,
        }
    ]
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers, ensure_ascii=False))
    monkeypatch.setattr(demo, "ANSWERS", path)
    monkeypatch.setattr(demo, "SITE", tmp_path / "_site")
    demo.build_site()
    page = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "Texte avec <\\/script> dedans." in page
    assert page.count("</script>") == 1
    assert "legi-data 2.565.0 et kali-data 3.504.0" in page


def test_every_group_has_questions():
    assert all(demo.QUESTIONS.values())
    assert sum(len(q) for q in demo.QUESTIONS.values()) == 14
