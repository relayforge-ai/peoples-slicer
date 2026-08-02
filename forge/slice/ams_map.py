"""REL-598 — build Bambu AMS tray mapping from color names / hex list.

``ams_mapping[i]`` = 0-based AMS tray for gcode filament i.
Studio default (German Shepherd 6/29): tan/black/white → trays [3, 0, 1].
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Default AMS loadout (override via ~/.forge/ams_stock.json or FORGE_AMS_STOCK)
DEFAULT_TRAYS: list[dict[str, Any]] = [
    {"tray": 0, "color": "black", "hex": "#000000"},
    {"tray": 1, "color": "white", "hex": "#FFFFFF"},
    {"tray": 2, "color": "red", "hex": "#C12E1F"},
    {"tray": 3, "color": "tan", "hex": "#AE835B"},
]


def load_stock(path: Path | None = None) -> list[dict[str, Any]]:
    path = Path(
        path
        or os.environ.get("FORGE_AMS_STOCK", str(Path.home() / ".forge" / "ams_stock.json"))
    )
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            trays = data.get("trays") or data.get("spools") or data
            if isinstance(trays, list) and trays:
                return trays
        except (OSError, json.JSONDecodeError):
            pass
    return list(DEFAULT_TRAYS)


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _hex_close(a: str, b: str) -> bool:
    a, b = a.lstrip("#").lower(), b.lstrip("#").lower()
    if len(a) != 6 or len(b) != 6:
        return a == b
    try:
        ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
        br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    except ValueError:
        return False
    return abs(ar - br) + abs(ag - bg) + abs(ab - bb) < 80


def map_colors_to_ams(
    colors: list[str],
    *,
    stock: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return ams_mapping list and unmatched colors.

    Accepts color names (\"tan\", \"black\") or hex (\"#AE835B\").
    """
    stock = stock or load_stock()
    mapping: list[int] = []
    unmatched: list[str] = []
    for c in colors:
        raw = (c or "").strip()
        if not raw:
            continue
        n = _norm(raw)
        hit = None
        for tray in stock:
            tname = _norm(str(tray.get("color") or tray.get("name") or ""))
            thex = str(tray.get("hex") or tray.get("colour") or "")
            if n and (n in tname or tname in n):
                hit = int(tray.get("tray", tray.get("id", 0)))
                break
            if raw.startswith("#") and thex and _hex_close(raw, thex):
                hit = int(tray.get("tray", tray.get("id", 0)))
                break
            if thex and _norm(thex) == n:
                hit = int(tray.get("tray", tray.get("id", 0)))
                break
        if hit is None:
            unmatched.append(raw)
            # Fail soft: leave sequential tray guess for operator review
            mapping.append(len(mapping) % max(1, len(stock)))
        else:
            mapping.append(hit)
    return {
        "ams_mapping": mapping,
        "use_ams": len(mapping) > 1,
        "unmatched": unmatched,
        "colors": colors,
        "ok": len(unmatched) == 0,
    }
