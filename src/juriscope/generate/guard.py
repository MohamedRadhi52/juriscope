"""Garde-fous contre l'injection de prompt : filtre sur la question, contrôle de la réponse."""

import re

INJECTION = re.compile(
    r"(ignore|oublie)[sz]?\s+(toutes?\s+)?(tes|les|vos|ces)\s+(consignes|instructions|règles)"
    r"|(prompt|instructions?|consignes?)\s+(du\s+)?syst[eè]me"
    r"|tu es (désormais|maintenant|dorénavant) un"
    r"|nouvelle consigne",
    re.IGNORECASE,
)


def suspicious(question: str) -> bool:
    """Vrai si la question contient une formule classique d'injection."""
    return bool(INJECTION.search(question))


def leaks(answer: str, prompt: str) -> bool:
    """Vrai si la réponse recopie une phrase d'au moins six mots des consignes."""
    flat = " ".join(answer.split()).lower()
    sentences = (" ".join(s.split()).lower() for s in re.split(r"[.\n:;]", prompt))
    return any(len(s.split()) >= 6 and s in flat for s in sentences)
