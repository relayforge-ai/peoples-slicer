"""Local Studio GUI — brand, assets, health API, fail-closed bind."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from forge import BRAND, __version__
from forge.gui_server import GUI_DIR, make_handler, serve


def test_brand_has_no_telchar_or_secrets():
    blob = json.dumps(BRAND) + BRAND["product"] + BRAND["tagline"]
    low = blob.lower()
    assert "telchar" not in low
    assert "relayforge.tools" not in low
    assert "people" in low
    assert BRAND["cli"] == "forge"


def test_gui_assets_exist():
    assert (GUI_DIR / "index.html").is_file()
    assert (GUI_DIR / "styles.css").is_file()
    assert (GUI_DIR / "app.js").is_file()
    html = (GUI_DIR / "index.html").read_text(encoding="utf-8")
    assert "People's Slicer" in html
    assert "telchar" not in html.lower()


def test_serve_rejects_non_localhost():
    with pytest.raises(ValueError, match="localhost"):
        serve(host="0.0.0.0", port=9, open_browser=False)


def test_health_handler_json():
    Handler = make_handler(None)
    # Smoke: class is constructible; deep HTTP exercised manually via forge gui.
    assert Handler is not None
    assert __version__


def test_cli_lists_gui():
    from forge.cli import SUBCOMMANDS, build_parser

    assert "gui" in SUBCOMMANDS
    p = build_parser()
    args = p.parse_args(["gui", "--no-browser", "--port", "18765"])
    assert args.command == "gui"
    assert args.no_browser is True
