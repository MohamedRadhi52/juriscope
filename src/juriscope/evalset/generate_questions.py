"""Génère le jeu d'évaluation avec un modèle de langage, à partir d'articles tirés au hasard.

La vérité terrain est l'article source, ce qui dispense d'annoter pour mesurer la recherche.
Les questions déjà écrites dans data/questions/generated.jsonl ne sont jamais réécrites :
relancer complète un jeu interrompu et ne change rien à un jeu complet.
"""

import argparse
import json
import random
import re
import tarfile
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.generate.providers import anthropic_complete, mistral_complete
from juriscope.ingest import parse
from juriscope.paths import DATA, RAW, SOURCES

# fournisseur par défaut, puis alternative si une clé Mistral est disponible
PROVIDERS = {
    "anthropic": (anthropic_complete, "claude-haiku-4-5-20251001"),
    "mistral": (mistral_complete, "mistral-large-latest"),
}
SEED = 2026
OUTPUT = DATA / "questions" / "generated.jsonl"
CODE_SECURITE_SOCIALE = "LEGITEXT000006073189"

# Nombre de questions par partie du Code, par convention, ou au total (hors corpus)
COUNTS = {
    "factuelle": 15,
    "paraphrase": 5,
    "multi-articles": 5,
    "factuelle convention": 6,
    "convention contre code": 4,
    "hors corpus": 40,
}

OUTRE_MER = re.compile(
    r"outre-mer|Mayotte|Guadeloupe|Guyane|Martinique|Réunion|Saint-Pierre|Saint-Martin",
    re.IGNORECASE,
)
CODE_REFERENCE = re.compile(r"\bL\.?\s?(\d{4}-\d+(?:-\d+)*)")
PARTS = ("Partie législative", "Partie réglementaire")
CSS_BOOKS = tuple(
    f"Code de la sécurité sociale > Partie législative > Livre {n} " for n in ("III", "V", "VIII")
)

RULES = """Règles :
- la question se comprend sans avoir lu l'article ;
- elle ne cite aucun numéro d'article et ne recopie pas les phrases du texte ;
- une seule question, en une phrase, terminée par un point d'interrogation ;
- si l'article ne permet aucune question utile (simple renvoi à un décret, disposition
  purement technique), réponds {"question": ""}."""
ONE_SOURCE = (
    'Réponds uniquement en JSON : {"question": "...", "reponse": "réponse courte", '
    '"extrait": "passage de l\'article, copié mot pour mot, qui justifie la réponse"}'
)
TWO_SOURCES = (
    'Réponds uniquement en JSON : {"question": "...", "reponse": "réponse courte", '
    '"extraits": ["passage du premier article, copié mot pour mot", '
    '"passage du second article, copié mot pour mot"]}'
)
INSTRUCTIONS = {
    "factuelle": "Écris une question qu'un salarié ou un employeur pourrait se poser, dont la "
    "réponse se trouve dans cet article. La question ne mentionne aucune convention collective.",
    "paraphrase": "Écris une question qu'un salarié pourrait poser avec ses propres mots, dont la "
    "réponse se trouve dans cet article. N'emploie aucun des termes juridiques de l'article : "
    "décris la situation concrète avec des mots courants.",
    "multi-articles": "Écris une question dont la réponse complète demande les deux articles.",
    "factuelle convention": "Écris une question qu'un salarié de cette branche pourrait se poser, "
    "dont la réponse se trouve dans cet article. La question nomme la convention par son nom "
    "courant : {name}.",
    "convention contre code": "Écris une question qui demande ce que la convention prévoit par "
    "rapport au Code du travail sur ce point. La question nomme la convention par son nom "
    "courant : {name}.",
    "hors corpus": "Écris une question qu'un salarié pourrait poser à un assistant de droit du "
    "travail, dont la réponse se trouve dans cet article. Elle porte sur la sécurité sociale "
    "(prestations, cotisations, retraite) et non sur le contrat de travail.",
}
HEADERS = {
    "factuelle": "Article du Code du travail :",
    "paraphrase": "Article du Code du travail :",
    "multi-articles": "Deux articles voisins du Code du travail :",
    "factuelle convention": "Article d'une convention collective :",
    "convention contre code": "Un article de convention collective, puis l'article du Code du "
    "travail qu'il cite :",
    "hors corpus": "Article du Code de la sécurité sociale :",
}


def eligible(article: dict) -> bool:
    """Article de longueur raisonnable, hors dispositions propres à l'outre-mer."""
    return 200 <= len(article["text"]) <= 3000 and not OUTRE_MER.search(" ".join(article["path"]))


def prompt(kind: str, sources: list[dict]) -> str:
    name = parse.CONVENTIONS[sources[0]["idcc"][0]] if sources[0]["idcc"] else ""
    articles = "\n\n".join(f"{a['title']}\n{a['text']}" for a in sources)
    output = TWO_SOURCES if len(sources) == 2 else ONE_SOURCE
    instruction = INSTRUCTIONS[kind].format(name=name)
    return (
        "Tu prépares des questions pour évaluer un assistant de droit du travail français.\n\n"
        f"{HEADERS[kind]}\n\n{articles}\n\n{instruction}\n{RULES}\n\n{output}"
    )


def build_tasks(corpus: list[dict], css: list[dict], counts: dict, seed: int) -> list[dict]:
    """Tire les articles sources de chaque question, sans réutiliser un article."""
    rng = random.Random(seed)
    used: set[str] = set()

    def draw(candidates: list, n: int) -> list:
        chosen = []
        for group in rng.sample(candidates, len(candidates)):
            if len(chosen) < n and used.isdisjoint(a["cid"] for a in group):
                chosen.append(group)
                used.update(a["cid"] for a in group)
        return chosen

    code = [a for a in corpus if not a["idcc"] and a["path"][1] in PARTS and eligible(a)]
    by_part: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    sections = defaultdict(list)
    for article in code:
        by_part[article["path"][2]][article["path"][1]].append([article])
        if article["path"][1] == PARTS[0]:
            sections[tuple(article["path"])].append(article)

    tasks = []
    # les huit parties du Code, sans le chapitre préliminaire (articles L1 à L3)
    for part in sorted(p for p in by_part if " partie :" in p):
        legislative, regulatory = by_part[part][PARTS[0]], by_part[part][PARTS[1]]
        n = counts["factuelle"]
        tasks += [("factuelle", g) for g in draw(legislative, n - n // 3)]
        tasks += [("factuelle", g) for g in draw(regulatory, n // 3)]
        tasks += [("paraphrase", g) for g in draw(legislative, counts["paraphrase"])]
        pairs = [
            s[i : i + 2]
            for path, s in sections.items()
            if path[2] == part
            for i in range(len(s) - 1)
        ]
        tasks += [("multi-articles", g) for g in draw(pairs, counts["multi-articles"])]

    code_by_num = {a["num"]: a for a in code}
    for idcc in parse.CONVENTIONS:
        articles = [a for a in corpus if idcc in a["idcc"] and eligible(a)]
        singles = [[a] for a in articles]
        tasks += [
            ("factuelle convention", g) for g in draw(singles, counts["factuelle convention"])
        ]
        cited = []
        for article in articles:
            nums = sorted({f"L{n}" for n in CODE_REFERENCE.findall(article["text"])})
            cited += [[article, code_by_num[n]] for n in nums if n in code_by_num]
        tasks += [
            ("convention contre code", g) for g in draw(cited, counts["convention contre code"])
        ]

    outside = [[a] for a in css if " > ".join(a["path"]).startswith(CSS_BOOKS) and eligible(a)]
    tasks += [("hors corpus", g) for g in draw(outside, counts["hors corpus"])]

    return [
        {
            "id": f"q{i:04d}",
            "type": "factuelle" if kind == "factuelle convention" else kind,
            "sources": [{"cid": a["cid"], "title": a["title"]} for a in sources],
            "relevant": [] if kind == "hors corpus" else [a["cid"] for a in sources],
            "prompt": prompt(kind, sources),
        }
        for i, (kind, sources) in enumerate(tasks, 1)
    ]


def generate(tasks: list[dict], output: Path, complete: Callable, model: str) -> int:
    """Écrit la réponse du modèle pour chaque tâche absente du fichier ; renvoie leur nombre."""
    done = {row["id"] for row in read_jsonl(output)} if output.exists() else set()
    todo = [task for task in tasks if task["id"] not in done]
    output.parent.mkdir(parents=True, exist_ok=True)
    for number, task in enumerate(todo, 1):
        answer = complete(task["prompt"], model)
        row = {key: value for key, value in task.items() if key != "prompt"}
        with output.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row | answer, ensure_ascii=False) + "\n")
        print(f"{number}/{len(todo)} {task['id']} {task['type']}")
    return len(todo)


def load_css() -> list[dict]:
    """Articles du Code de la sécurité sociale, source des questions hors corpus."""
    version = json.loads(SOURCES.read_text())["@socialgouv/legi-data"]["version"]
    with tarfile.open(RAW / f"legi-data-{version}.tgz") as tar:
        code = tar.extractfile(f"package/data/{CODE_SECURITE_SOCIALE}.json")
        return list(parse.legi_articles(json.load(code)))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.evalset.generate_questions")
    parser.add_argument("--provider", choices=PROVIDERS, default="anthropic")
    complete, model = PROVIDERS[parser.parse_args().provider]
    tasks = build_tasks(load_corpus(), load_css(), COUNTS, SEED)
    written = generate(tasks, OUTPUT, complete, model)
    print(f"{written} questions générées, {len(tasks)} au total dans {OUTPUT.name}")


if __name__ == "__main__":
    main()
