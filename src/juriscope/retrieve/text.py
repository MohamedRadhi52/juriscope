"""Tokenisation française pour BM25."""

import re
import unicodedata
from functools import cache

import Stemmer
from bm25s.stopwords import STOPWORDS_FRENCH

# Particules élidées (l', qu', jusqu'...) et "a", très fréquent dans les textes de loi
STOPWORDS = frozenset(STOPWORDS_FRENCH) | {"a", "jusqu", "lorsqu", "puisqu", "quoiqu"}

TOKEN = re.compile(
    r"(?P<ref>\b[LRD]\.?\s?\d+(?:-\d+)*\b)"  # référence d'article : L. 1234-1, R4451-39
    r"|(?P<acronym>\b(?:[A-Z]\.){2,}|\b[A-Z]{2,6}\b)"  # sigle : CSE, C.D.D.
    r"|(?P<word>\w+(?:\.\d+)*)"  # mot ou nombre, y compris 3.4
)
STEMMER = Stemmer.Stemmer("french")


@cache
def stem(word: str) -> str:
    """Racine sans accents : les accents sont retirés avant, pour que salariés et salaries
    donnent la même racine."""
    folded = unicodedata.normalize("NFKD", word.replace("œ", "oe").replace("æ", "ae"))
    return STEMMER.stemWord(folded.encode("ascii", "ignore").decode())


def tokenize(text: str) -> list[str]:
    tokens = []
    for match in TOKEN.finditer(text):
        ref, acronym, word = match.group("ref", "acronym", "word")
        if ref:
            tokens.append(re.sub(r"[.\s]", "", ref).lower())
        elif acronym:
            # un sigle garde sa forme et n'est jamais un mot vide : le CE n'est pas "ce"
            tokens.append(acronym.replace(".", "").lower())
        elif (lower := word.lower()) not in STOPWORDS:
            tokens.append(stem(lower))
    return tokens
