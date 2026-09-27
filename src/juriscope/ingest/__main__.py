"""Télécharge les versions du corpus épinglées dans data/sources.json."""

import argparse
import json

from juriscope.ingest import npm
from juriscope.paths import RAW, ROOT, SOURCES


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m juriscope.ingest")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="signale les nouvelles versions")
    action.add_argument("--update", action="store_true", help="épingle les dernières versions")
    args = parser.parse_args()

    sources = json.loads(SOURCES.read_text())

    if args.check or args.update:
        for package, pin in sources.items():
            last = npm.latest(package)
            if last["version"] == pin["version"]:
                print(f"{package} {pin['version']} : à jour")
            else:
                print(f"{package} {pin['version']} : version {last['version']} disponible")
                sources[package] = last
        if args.update:
            SOURCES.write_text(json.dumps(sources, indent=2) + "\n")
        return

    for package, pin in sources.items():
        path = npm.ensure_tarball(package, pin["version"], pin["integrity"], RAW)
        print(f"{package} {pin['version']} : {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
