"""Load captured hardware truth so tests never need a live printer.

Layout:  fixtures/<printer>/<name>.json   (parsed)  |  <name>.<ext>  (raw text)
Printers: bambu_a2l | ad5x | ender
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


class FixtureNotFound(FileNotFoundError):
    def __init__(self, printer: str, name: str):
        super().__init__(
            f"No fixture {printer!r}/{name!r}. Capture it on hardware first — "
            f"see docs/superpowers/plans/2026-07-01-phase0-scaffold-and-capture.md (Part B)."
        )


def _dir(printer: str) -> Path:
    return FIXTURES_ROOT / printer


def load(printer: str, name: str) -> dict:
    path = _dir(printer) / f"{name}.json"
    if not path.exists():
        raise FixtureNotFound(printer, name)
    return json.loads(path.read_text())


def load_text(printer: str, name: str) -> str:
    path = _dir(printer) / name
    if not path.exists():
        raise FixtureNotFound(printer, name)
    return path.read_text()


def available(printer: str) -> list[str]:
    d = _dir(printer)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))
