"""Accord entre deux séries d'étiquettes binaires : kappa de Cohen et intervalle bootstrap."""

import numpy as np


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    """Accord corrigé du hasard ; vaut 1 pour un accord parfait, 0 pour un accord de hasard."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    observed = np.mean(a == b)
    chance = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    # cas dégénéré d'un tirage où les deux séries ne contiennent qu'une seule valeur
    return 1.0 if chance == 1 else float((observed - chance) / (1 - chance))


def kappa_ci(a: list[bool], b: list[bool], n_resamples: int = 2000, seed: int = 0) -> tuple:
    """Intervalle à 95 % du kappa, en tirant les paires d'étiquettes avec remise."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    samples = rng.integers(0, len(a), size=(n_resamples, len(a)))
    kappas = [cohen_kappa(a[i], b[i]) for i in samples]
    low, high = np.quantile(kappas, [0.025, 0.975])
    return float(low), float(high)
