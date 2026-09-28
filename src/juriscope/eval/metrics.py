"""Métriques de recherche, avec pertinence binaire, et intervalles bootstrap."""

import math

import numpy as np


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(relevant.intersection(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str], k: int) -> float:
    return next((1 / rank for rank, cid in enumerate(ranked[:k], 1) if cid in relevant), 0.0)


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(1 / math.log2(rank + 1) for rank, cid in enumerate(ranked[:k], 1) if cid in relevant)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(relevant), k) + 1))
    return dcg / ideal


def bootstrap_ci(
    values: list[float], n_resamples: int = 2000, seed: int = 0
) -> tuple[float, float]:
    """Intervalle de confiance à 95 % de la moyenne, par la méthode des percentiles."""
    rng = np.random.default_rng(seed)
    samples = rng.choice(np.asarray(values, dtype=float), size=(n_resamples, len(values)))
    low, high = np.quantile(samples.mean(axis=1), [0.025, 0.975])
    return float(low), float(high)


def paired_gain_ci(before: list[float], after: list[float], n_resamples: int = 2000, seed: int = 0):
    """Gain moyen d'une méthode sur l'autre et son intervalle à 95 %, questions tirées ensemble."""
    rng = np.random.default_rng(seed)
    gains = np.asarray(after, dtype=float) - np.asarray(before, dtype=float)
    samples = rng.choice(gains, size=(n_resamples, len(gains)))
    low, high = np.quantile(samples.mean(axis=1), [0.025, 0.975])
    return float(gains.mean()), float(low), float(high)
