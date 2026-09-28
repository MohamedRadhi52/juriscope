"""Calcule les vecteurs des passages et des questions, dans GitHub Actions.

Le calcul peut être découpé en morceaux (--shard, --shards) lancés en parallèle, puis réunis
avec --merge. Les fichiers de data/index/ sont publiés en asset de release.
"""

import argparse
import json

import numpy as np

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.eval import bsard
from juriscope.paths import DATA, SOURCES
from juriscope.retrieve.dense import INDEX, MODEL, passages


def save(path, keys: list[str], vectors: np.ndarray) -> None:
    np.savez_compressed(
        path, keys=np.array(keys), vectors=vectors.astype(np.float16), sources=SOURCES.read_text()
    )


def merge(prefix: str, shards: int) -> None:
    parts = [np.load(INDEX / f"{prefix}passages-{i}.npz") for i in range(shards)]
    keys = np.concatenate([part["keys"] for part in parts]).tolist()
    save(INDEX / f"{prefix}passages.npz", keys, np.concatenate([p["vectors"] for p in parts]))


def encode(model_name: str, articles: list, questions: list, prefix: str, shard: int, shards: int):
    # torch n'est installé que dans les jobs qui encodent
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    cids, texts = [], []
    for article in articles:
        for passage in passages(article):
            cids.append(article["cid"])
            texts.append(f"passage: {passage}")
    INDEX.mkdir(parents=True, exist_ok=True)
    part = slice(shard, None, shards)
    vectors = model.encode(texts[part], batch_size=64, normalize_embeddings=True)
    suffix = f"-{shard}" if shards > 1 else ""
    save(INDEX / f"{prefix}passages{suffix}.npz", cids[part], vectors)
    if shard == 0:
        vectors = model.encode([f"query: {q}" for q in questions], normalize_embeddings=True)
        save(INDEX / f"{prefix}questions.npz", questions, vectors)
    print(json.dumps({"passages": len(cids[part]), "modele": model_name, "morceau": shard}))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.retrieve.embed")
    parser.add_argument("--model", default=MODEL, help="nom Hugging Face ou dossier local")
    parser.add_argument("--name", default="", help="préfixe des fichiers, par exemple ft")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--merge", action="store_true", help="réunit les morceaux calculés")
    parser.add_argument("--corpus", choices=["juriscope", "bsard"], default="juriscope")
    args = parser.parse_args()
    prefix = f"{args.name}-" if args.name else ""
    if args.merge:
        merge(prefix, args.shards)
        return
    if args.corpus == "bsard":
        articles, questions = bsard.load_articles(), [q["question"] for q in bsard.load_questions()]
    else:
        files = [DATA / "questions" / name for name in ("eval.jsonl", "pilote.jsonl")]
        articles = load_corpus()
        questions = sorted({q["question"] for f in files for q in read_jsonl(f)})
    encode(args.model, articles, questions, prefix, args.shard, args.shards)


if __name__ == "__main__":
    main()
