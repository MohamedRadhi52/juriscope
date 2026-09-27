import io

import pytest

from juriscope.ingest import npm


def test_integrity_matches_npm_format(tmp_path):
    path = tmp_path / "vide"
    path.write_bytes(b"")
    # SHA-512 du contenu vide, en base64 comme le champ dist.integrity de npm
    assert npm.integrity(path) == (
        "sha512-z4PhNX7vuL3xVChQ1m2AB9Yg5AULVxXcg/SpIdNs6c5H0NE8XYXysP+DGNKHfuwvY7kxvUdBeoGlODJ6"
        "+SfaPg=="
    )


def test_present_tarball_is_not_downloaded_again(tmp_path, monkeypatch):
    path = tmp_path / "legi-data-1.0.0.tgz"
    path.write_bytes(b"archive")

    def fail(*args, **kwargs):
        raise AssertionError("aucun téléchargement attendu")

    monkeypatch.setattr(npm, "urlopen", fail)
    result = npm.ensure_tarball("@socialgouv/legi-data", "1.0.0", npm.integrity(path), tmp_path)
    assert result == path


def test_download_is_checked_against_integrity(tmp_path, monkeypatch):
    reference = tmp_path / "reference"
    reference.write_bytes(b"archive")
    expected = npm.integrity(reference)
    raw = tmp_path / "raw"

    monkeypatch.setattr(npm, "urlopen", lambda url, timeout: io.BytesIO(b"archive"))
    path = npm.ensure_tarball("@socialgouv/kali-data", "2.0.0", expected, raw)
    assert path.read_bytes() == b"archive"

    monkeypatch.setattr(npm, "urlopen", lambda url, timeout: io.BytesIO(b"corrompue"))
    with pytest.raises(ValueError, match="empreinte"):
        npm.ensure_tarball("@socialgouv/kali-data", "3.0.0", expected, raw)
    assert sorted(p.name for p in raw.iterdir()) == ["kali-data-2.0.0.tgz"]
