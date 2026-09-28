"""Archives npm du corpus, vérifiées par leur empreinte sha512."""

import base64
import hashlib
import json
import shutil
from pathlib import Path
from urllib.request import urlopen

REGISTRY = "https://registry.npmjs.org"


def integrity(path: Path) -> str:
    """Empreinte d'un fichier au format npm : sha512-<base64>."""
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha512").digest()
    return "sha512-" + base64.b64encode(digest).decode()


def ensure_tarball(package: str, version: str, expected: str, raw_dir: Path) -> Path:
    """Télécharge l'archive si elle manque ; relancer ne retélécharge rien."""
    path = raw_dir / f"{package.split('/')[-1]}-{version}.tgz"
    if path.exists() and integrity(path) == expected:
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    url = f"{REGISTRY}/{package}/-/{path.name}"
    with urlopen(url, timeout=60) as response, part.open("wb") as f:
        shutil.copyfileobj(response, f)
    if integrity(part) != expected:
        part.unlink()
        raise ValueError(f"empreinte inattendue pour {package}@{version}")
    part.replace(path)
    return path


def release(package: str, version: str = "latest") -> dict:
    """Version publiée d'un paquet (la dernière par défaut) et son empreinte."""
    with urlopen(f"{REGISTRY}/{package}/{version}", timeout=30) as response:
        meta = json.load(response)
    return {"version": meta["version"], "integrity": meta["dist"]["integrity"]}
