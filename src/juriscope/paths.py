"""Emplacements des données du projet."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
SOURCES = DATA / "sources.json"
