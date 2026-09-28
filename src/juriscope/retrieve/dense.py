"""Recherche dense : vecteurs des passages dans Qdrant en mode local, meilleur passage par article.

Les vecteurs sont calculés dans GitHub Actions par python -m juriscope.retrieve.embed, puis
publiés en asset de release et téléchargés dans data/index/.
"""

import json
import warnings
from collections.abc import Callable
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from juriscope.paths import DATA, SOURCES

INDEX = DATA / "index"
MODEL = "intfloat/multilingual-e5-small"
PASSAGE_WORDS, STRIDE = 250, 200


def passages(article: dict) -> list[str]:
    """Fenêtres de 250 mots qui se chevauchent, pour tenir dans les 512 jetons du modèle.

    Chaque passage commence par le titre et la section de l'article, qui portent souvent les
    mots de la question (le nom de la convention, par exemple).
    """
    header = f"{article['title']} | {article['path'][-1]}"
    words = article["text"].split()
    chunks = []
    for start in range(0, len(words), STRIDE):
        chunks.append(f"{header}\n{' '.join(words[start : start + PASSAGE_WORDS])}")
        if start + PASSAGE_WORDS >= len(words):
            break
    return chunks


def load_vectors(path: Path) -> tuple[list[str], np.ndarray]:
    """Clés et vecteurs d'un fichier produit par embed ; refuse une autre version du corpus."""
    data = np.load(path)
    if json.loads(str(data["sources"])) != json.loads(SOURCES.read_text()):
        raise ValueError(f"{path.name} vient d'une autre version du corpus : relancer embed")
    return data["keys"].tolist(), data["vectors"].astype(np.float32)


class Dense:
    def __init__(self, cids: list[str], vectors: np.ndarray, encode: Callable):
        self.encode = encode
        self.client = QdrantClient(":memory:")
        self.client.create_collection(
            "passages", vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE)
        )
        # le mode local avertit au-delà de 20 000 points ; il suffit pour une évaluation
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Local mode is not recommended")
            self.client.upload_collection(
                "passages", vectors=vectors, payload=[{"cid": cid} for cid in cids]
            )

    @classmethod
    def from_index(cls, name: str = "", encode: Callable | None = None) -> Dense:
        """Index des passages ; les questions sont encodées par encode, ou lues dans les
        vecteurs calculés à l'avance.

        name choisit un jeu de vecteurs : "" pour le modèle de base, "ft" pour le modèle affiné.
        """
        prefix = f"{name}-" if name else ""
        if encode is None:
            questions, vectors = load_vectors(INDEX / f"{prefix}questions.npz")
            encode = dict(zip(questions, vectors, strict=True)).__getitem__
        return cls(*load_vectors(INDEX / f"{prefix}passages.npz"), encode)

    def search(self, query: str, k: int = 10) -> list[str]:
        """Identifiants communs des k articles dont un passage est le plus proche."""
        hits = self.client.query_points("passages", query=self.encode(query), limit=5 * k).points
        return list(dict.fromkeys(hit.payload["cid"] for hit in hits))[:k]
