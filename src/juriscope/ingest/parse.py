"""Aplatissement des arbres JSON de LEGI et KALI en articles.

Chaque article est un dict : id (version), cid (identifiant commun), num, title, path
(sections depuis la racine), text, state, start et end (dates ISO, None si inconnues ou
sans fin), idcc (liste vide pour le Code du travail) et in_force.
"""

import html
import json
import re
import statistics
import tarfile
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

CODE_DU_TRAVAIL = "LEGITEXT000006072050"

# À incrémenter quand le schéma des articles change, pour reconstruire le corpus
FORMAT = 2

# Conventions retenues (docs/DECISIONS.md) et nom court affiché dans les citations
CONVENTIONS = {
    "1486": "Syntec",
    "3248": "Métallurgie",
    "2216": "Commerce à prédominance alimentaire",
    "0016": "Transports routiers",
    "1979": "HCR",
    "0413": "CCN 66",
    "1090": "Services de l'automobile",
    "3043": "Propreté",
    "2120": "Banque",
    "1672": "Sociétés d'assurances",
}

BLOCK_END = re.compile(r"<(?:br|/p|/li|/tr|/h\d|/div)\b[^>]*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


def html_to_text(fragment: str) -> str:
    """Texte brut d'un fragment HTML, un paragraphe par ligne."""
    text = html.unescape(TAG.sub(" ", BLOCK_END.sub("\n", fragment)))
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def clean(title: str) -> str:
    return " ".join(title.split())


def iso_date(ms: int) -> str | None:
    """Date ISO d'un horodatage LEGI en millisecondes ; l'an 2999 signifie sans fin."""
    day = datetime.fromtimestamp(ms / 1000, UTC).date()
    return None if day.year >= 2999 else day.isoformat()


def legi_articles(code: dict) -> Iterator[dict]:
    """Articles d'un code, avec l'indicateur de vigueur à la date de la version."""
    name = clean(code["data"]["title"])
    version_day = code["data"]["dateDebutVersion"]

    def walk(node: dict, path: list[str]) -> Iterator[dict]:
        for child in node["children"]:
            data = child["data"]
            if child["type"] == "section":
                yield from walk(child, [*path, clean(data["title"])])
                continue
            start, end = iso_date(data["dateDebut"]), iso_date(data["dateFin"])
            num = clean(data["num"])
            yield {
                "id": data["id"],
                "cid": data["cid"],
                "num": num,
                "title": f"{name}, {num if num.startswith('Annexe') else f'art. {num}'}",
                "path": path,
                "text": html_to_text(data["texteHtml"]),
                "state": data["etat"],
                "start": start,
                "end": end,
                "idcc": [],
                "in_force": start <= version_day and (end is None or version_day < end),
            }

    yield from walk(code, [name])


def kali_articles(convention: dict, idcc: str) -> Iterator[dict]:
    """Articles du texte de base et des textes attachés, sans les textes salaires."""
    name = f"{CONVENTIONS[idcc]} (IDCC {idcc})"
    root = f"Convention collective {name} : {clean(convention['data']['shortTitle'])}"

    def walk(node: dict, path: list[str], text: str) -> Iterator[dict]:
        for child in node["children"]:
            data = child["data"]
            if child["type"] == "section":
                yield from walk(child, [*path, clean(data["title"])], text)
                continue
            num, heading = clean(data.get("num") or ""), clean(data.get("surtitre") or "")
            # sans numéro ni intitulé, on nomme la section, sauf si c'est le texte lui-même
            label = f"art. {num}" if num else heading or (path[-1] if len(path) > 2 else "")
            if num and heading:
                label += f" : {heading}"
            yield {
                "id": data["id"],
                "cid": data["cid"],
                "num": num,
                "title": ", ".join(part for part in (name, text, label) if part),
                "path": path,
                "text": html_to_text(data.get("content") or ""),
                "state": data["etat"],
                "start": None,
                "end": None,
                "idcc": [idcc],
                "in_force": data["etat"].startswith("VIGUEUR"),
            }

    base, attached, _salaries = convention["children"]
    yield from walk(base, [root, clean(base["data"]["title"])], "texte de base")
    for text in attached["children"]:
        title = clean(text["data"]["title"])
        yield from walk(text, [root, title], title)


def merge_shared(articles: list[dict]) -> list[dict]:
    """Fusionne les articles rattachés à plusieurs conventions (même id)."""
    by_id: dict[str, dict] = {}
    for article in articles:
        if article["id"] in by_id:
            by_id[article["id"]]["idcc"] += article["idcc"]
        else:
            by_id[article["id"]] = article
    return list(by_id.values())


def build_corpus(legi_tgz: Path, kali_tgz: Path) -> tuple[list[dict], dict]:
    """Articles en vigueur du Code du travail et des conventions retenues, et statistiques."""
    with tarfile.open(legi_tgz) as tar:
        code = tar.extractfile(f"package/data/{CODE_DU_TRAVAIL}.json")
        parsed = list(legi_articles(json.load(code)))

    with tarfile.open(kali_tgz) as tar:
        index = {c["num"]: c for c in json.load(tar.extractfile("package/data/index.json"))}
        for idcc in CONVENTIONS:
            convention = json.load(tar.extractfile(f"package/data/{index[idcc]['id']}.json"))
            parsed += kali_articles(convention, idcc)

    kept = merge_shared([a for a in parsed if a["in_force"] and a["text"]])
    lengths = sorted(len(a["text"]) for a in kept)
    texts = Counter(a["text"] for a in kept)
    stats = {
        "articles": len(kept),
        "code_du_travail": sum(1 for a in kept if not a["idcc"]),
        "conventions": {idcc: sum(1 for a in kept if idcc in a["idcc"]) for idcc in CONVENTIONS},
        "exclus_hors_vigueur": sum(1 for a in parsed if not a["in_force"]),
        "exclus_texte_vide": sum(1 for a in parsed if a["in_force"] and not a["text"]),
        "partages_entre_conventions": sum(1 for a in kept if len(a["idcc"]) > 1),
        "textes_en_double": sum(n for n in texts.values() if n > 1),
        "longueur_mediane": int(statistics.median(lengths)),
        "longueur_p95": lengths[int(0.95 * len(lengths))],
        "longueur_max": lengths[-1],
    }
    return kept, stats
