"""Outils de l'agent : lecture d'un article, métadonnées des conventions en SQL, veille."""

import json
import re
import sqlite3
import tarfile
from pathlib import Path

from juriscope.ingest.parse import CONVENTIONS
from juriscope.paths import CORPUS, RAW, ROOT, SOURCES

DATABASE = CORPUS / "conventions.sqlite"
VEILLE = ROOT / "results" / "veille" / "rapport.json"
ARTICLE_NUMBER = re.compile(r"\b([LRD])\.?\s?(\d{4}-\d+(?:-\d+)*)", re.IGNORECASE)


def find_article(entree: str, code_articles: dict) -> dict:
    """Texte d'un article du Code désigné par son numéro : L1234-1, L. 1234-1 ou l1234-1."""
    match = ARTICLE_NUMBER.search(entree)
    article = code_articles.get(f"{match[1].upper()}{match[2]}") if match else None
    if article is None:
        return {"erreur": f"aucun article du Code du travail ne correspond à {entree!r}"}
    return {"cid": article["cid"], "titre": article["title"], "texte": article["text"][:1500]}


def build_database(articles: list[dict]) -> Path:
    """Table conventions(idcc, nom, titre, salaries, articles) des conventions du corpus."""
    version = json.loads(SOURCES.read_text())["@socialgouv/kali-data"]["version"]
    with tarfile.open(RAW / f"kali-data-{version}.tgz") as tar:
        index = {c["num"]: c for c in json.load(tar.extractfile("package/data/index.json"))}
    rows = [
        (
            idcc,
            name,
            index[idcc]["shortTitle"],
            index[idcc]["effectif"],
            sum(1 for a in articles if idcc in a["idcc"]),
        )
        for idcc, name in CONVENTIONS.items()
    ]
    DATABASE.unlink(missing_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            "CREATE TABLE conventions "
            "(idcc TEXT, nom TEXT, titre TEXT, salaries INTEGER, articles INTEGER)"
        )
        connection.executemany("INSERT INTO conventions VALUES (?, ?, ?, ?, ?)", rows)
    return DATABASE


def query_conventions(sql: str, database: Path = DATABASE) -> dict:
    """Requête en lecture seule : une seule instruction SELECT, sur une base ouverte en lecture.

    La requête vient d'un modèle de langage : une erreur est renvoyée à l'agent, qui peut
    corriger sa requête.
    """
    if not sql.strip().lower().startswith("select"):
        return {"erreur": "seules les requêtes SELECT sont permises"}
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        try:
            cursor = connection.execute(sql)
        except sqlite3.Error as error:
            return {"erreur": str(error)}
        columns = [c[0] for c in cursor.description]
        return {"lignes": [dict(zip(columns, row, strict=True)) for row in cursor.fetchmany(50)]}


def veille_summary(report: Path = VEILLE) -> dict:
    """Résumé du dernier rapport de veille : versions comparées et articles touchés."""
    data = json.loads(report.read_text())
    return {key: data[key] for key in ("de", "vers", "ajoutes", "supprimes", "modifies")} | {
        "articles_modifies": [a["titre"] for a in data["articles_modifies"]]
    }
