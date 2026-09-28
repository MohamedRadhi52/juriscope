from juriscope.eval import bsard

ARTICLES = 'id,reference,article\n1,Art. 1,"Le bail est conclu pour neuf ans."\n2,Art. 2,Autre.\n'
QUESTIONS = 'id,question,article_ids\n10,Combien de temps dure un bail ?,"1,2"\n'


class Fixed:
    def search(self, query, k):
        return ["2", "3", "1"][:k]


def test_csv_files_are_read_in_the_corpus_format(tmp_path, monkeypatch):
    monkeypatch.setattr(bsard, "BSARD", tmp_path)
    (tmp_path / "articles.csv").write_text(ARTICLES, encoding="utf-8")
    (tmp_path / "questions_test.csv").write_text(QUESTIONS, encoding="utf-8")
    first = bsard.load_articles()[0]
    assert (first["cid"], first["text"], first["title"]) == (
        "1",
        "Le bail est conclu pour neuf ans.",
        "Article 1",
    )
    assert bsard.load_questions() == [
        {"id": "10", "question": "Combien de temps dure un bail ?", "relevant": ["1", "2"]}
    ]


def test_measure_reports_recall_at_100_and_reciprocal_rank():
    questions = [{"question": "Q ?", "relevant": ["1", "2"]}]
    result = bsard.measure(Fixed(), questions)
    assert result["r@100"]["moyenne"] == 1.0
    assert result["mrr@100"]["moyenne"] == 1.0
    assert result["r@10"]["valeurs"] == [1.0]
