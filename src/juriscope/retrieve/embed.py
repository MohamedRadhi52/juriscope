"""Calcule les vecteurs des passages et des questions, dans GitHub Actions.

Le modèle vient de Hugging Face, inaccessible depuis certains postes : le workflow embed
publie les fichiers de data/index/ en asset de release.
"""

import json

import numpy as np
from sentence_transformers import SentenceTransformer

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.paths import DATA, SOURCES
from juriscope.retrieve.dense import INDEX, MODEL, passages


def save(path, keys: list[str], vectors: np.ndarray) -> None:
    np.savez_compressed(
        path, keys=np.array(keys), vectors=vectors.astype(np.float16), sources=SOURCES.read_text()
    )


def main() -> None:
    model = SentenceTransformer(MODEL)
    cids, texts = [], []
    for article in load_corpus():
        for passage in passages(article):
            cids.append(article["cid"])
            texts.append(f"passage: {passage}")
    INDEX.mkdir(parents=True, exist_ok=True)
    vectors = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=True)
    save(INDEX / "passages.npz", cids, vectors)

    files = [DATA / "questions" / name for name in ("eval.jsonl", "pilote.jsonl")]
    questions = sorted({q["question"] for f in files for q in read_jsonl(f)})
    vectors = model.encode([f"query: {q}" for q in questions], normalize_embeddings=True)
    save(INDEX / "questions.npz", questions, vectors)
    print(json.dumps({"passages": len(cids), "questions": len(questions), "modele": MODEL}))


if __name__ == "__main__":
    main()
