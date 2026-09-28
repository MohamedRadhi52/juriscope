import json

import numpy as np
import pytest

from juriscope.retrieve import dense


def article(text, title="Code du travail, art. L1", section="Section 1 : Congés"):
    return {"title": title, "path": ["Code du travail", section], "text": text}


def test_short_article_is_one_passage_with_its_title_and_section():
    [passage] = dense.passages(article("Le salarié a droit à un congé."))
    assert (
        passage == "Code du travail, art. L1 | Section 1 : Congés\nLe salarié a droit à un congé."
    )


def test_long_article_is_cut_into_overlapping_windows():
    words = [f"m{i}" for i in range(500)]
    chunks = dense.passages(article(" ".join(words)))
    bodies = [chunk.split("\n")[1].split() for chunk in chunks]
    assert [(b[0], b[-1]) for b in bodies] == [("m0", "m249"), ("m200", "m449"), ("m400", "m499")]


def test_search_keeps_the_best_passage_of_each_article():
    vectors = np.array([[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)
    queries = {"congés": np.array([1, 0.05, 0], dtype=np.float32)}
    index = dense.Dense(["A", "A", "B", "C"], vectors, queries.__getitem__)
    assert index.search("congés", k=2) == ["A", "B"]


def test_vectors_from_another_corpus_version_are_refused(tmp_path, monkeypatch):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"@socialgouv/legi-data": {"version": "1.0.0"}}))
    monkeypatch.setattr(dense, "SOURCES", sources)
    path = tmp_path / "passages.npz"
    old = json.dumps({"@socialgouv/legi-data": {"version": "0.9.0"}})
    np.savez(path, keys=np.array(["A"]), vectors=np.ones((1, 3)), sources=old)
    with pytest.raises(ValueError, match="autre version du corpus"):
        dense.load_vectors(path)
    np.savez(path, keys=np.array(["A"]), vectors=np.ones((1, 3)), sources=sources.read_text())
    assert dense.load_vectors(path)[0] == ["A"]
