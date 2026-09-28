"""Télécharge les versions du corpus épinglées dans data/sources.json et le découpe."""

import argparse
import json

from juriscope.ingest import npm, parse
from juriscope.paths import CORPUS, RAW, ROOT, SOURCES


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.ingest")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="signale les nouvelles versions")
    action.add_argument("--update", action="store_true", help="épingle les dernières versions")
    args = parser.parse_args()

    sources = json.loads(SOURCES.read_text())

    if args.check or args.update:
        for package, pin in sources.items():
            last = npm.release(package)
            if last["version"] == pin["version"]:
                print(f"{package} {pin['version']} : à jour")
            else:
                print(f"{package} {pin['version']} : version {last['version']} disponible")
                sources[package] = last
        if args.update:
            SOURCES.write_text(json.dumps(sources, indent=2) + "\n")
        return

    tarballs = {}
    for package, pin in sources.items():
        tarballs[package] = npm.ensure_tarball(package, pin["version"], pin["integrity"], RAW)
        print(f"{package} {pin['version']} : {tarballs[package].relative_to(ROOT)}")

    manifest_path = CORPUS / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["format"] == parse.FORMAT and manifest["sources"] == sources:
            print(f"corpus déjà à jour : {manifest['stats']['articles']} articles")
            return

    articles, stats = parse.build_corpus(
        tarballs["@socialgouv/legi-data"], tarballs["@socialgouv/kali-data"]
    )
    CORPUS.mkdir(parents=True, exist_ok=True)
    with (CORPUS / "articles.jsonl").open("w", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
    manifest = {"format": parse.FORMAT, "sources": sources, "stats": stats}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("corpus construit :")
    for key, value in stats.items():
        print(f"  {key} : {value}")


if __name__ == "__main__":
    main()
