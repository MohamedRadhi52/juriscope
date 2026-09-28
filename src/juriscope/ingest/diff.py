"""Veille : articles ajoutés, supprimés ou modifiés entre deux versions du corpus.

python -m juriscope.ingest.diff --old 2.552.0 3.485.0   des anciennes versions aux épinglées
python -m juriscope.ingest.diff --new latest            des épinglées aux dernières publiées
"""

import argparse
import json

from juriscope.corpus import read_jsonl
from juriscope.ingest import npm, parse
from juriscope.paths import DATA, RAW, ROOT, SOURCES

REPORT = ROOT / "results" / "veille" / "rapport.json"
TEMPORAL = DATA / "questions" / "temporelles.jsonl"
MAX_TEMPORAL = 30


def versions(spec: list[str] | None, pinned: dict) -> dict:
    """Versions et empreintes : épinglées par défaut, dernières publiées, ou données à la main."""
    if spec is None:
        return pinned
    if spec == ["latest"]:
        return {package: npm.release(package) for package in pinned}
    return {package: npm.release(package, v) for package, v in zip(pinned, spec, strict=True)}


def corpus_for(sources: dict) -> list[dict]:
    legi, kali = (
        npm.ensure_tarball(p, s["version"], s["integrity"], RAW) for p, s in sources.items()
    )
    return parse.build_corpus(legi, kali)[0]


def diff(old: list[dict], new: list[dict]) -> dict:
    """Compare par identifiant commun (cid), qui reste le même quand un article est modifié."""
    before, after = {a["cid"]: a for a in old}, {a["cid"]: a for a in new}
    return {
        "ajoutes": sorted(after.keys() - before.keys()),
        "supprimes": sorted(before.keys() - after.keys()),
        "modifies": sorted(
            c for c in before.keys() & after.keys() if before[c]["text"] != after[c]["text"]
        ),
    }


def affected(changes: dict, questions: list[dict]) -> list[str]:
    """Questions dont un article attendu a été modifié ou supprimé : leur réponse est à revoir."""
    touched = set(changes["modifies"]) | set(changes["supprimes"])
    return [q["id"] for q in questions if touched & set(q["relevant"])]


def temporal_questions(changes: dict, articles: dict) -> list[dict]:
    """Questions sur la rédaction en vigueur des articles du Code modifiés."""
    modified = [articles[c] for c in changes["modifies"] if not articles[c]["idcc"]]
    return [
        {
            "id": f"t{i:04d}",
            "type": "temporelle",
            "question": f"Que prévoit aujourd'hui l'article {a['num']} du Code du travail ?",
            "relevant": [a["cid"]],
            "refs": [a["title"]],
        }
        for i, a in enumerate(modified[:MAX_TEMPORAL], 1)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.ingest.diff")
    parser.add_argument("--old", nargs="+", metavar="VERSION", help="legi-data puis kali-data")
    parser.add_argument("--new", nargs="+", metavar="VERSION", help="versions, ou latest")
    args = parser.parse_args()
    pinned = json.loads(SOURCES.read_text())
    old, new = versions(args.old, pinned), versions(args.new, pinned)
    if old == new:
        print("versions identiques : rien à comparer")
        return
    after = corpus_for(new)
    changes = diff(corpus_for(old), after)
    by_cid = {a["cid"]: a for a in after}
    questions = read_jsonl(DATA / "questions" / "eval.jsonl")
    report = {
        "de": {p: s["version"] for p, s in old.items()},
        "vers": {p: s["version"] for p, s in new.items()},
        **{kind: len(cids) for kind, cids in changes.items()},
        "questions_touchees": affected(changes, questions),
        "articles_modifies": [{"cid": c, "titre": by_cid[c]["title"]} for c in changes["modifies"]],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.new is None:
        rows = temporal_questions(changes, by_cid)
        TEMPORAL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"De {report['de']} vers {report['vers']} :")
    added, removed, modified = report["ajoutes"], report["supprimes"], report["modifies"]
    print(f"- articles : {added} ajoutés, {removed} supprimés, {modified} modifiés")
    print(f"- {len(report['questions_touchees'])} questions du jeu d'évaluation à revoir")


if __name__ == "__main__":
    main()
