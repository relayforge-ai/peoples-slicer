"""Classify an OrcaSlicer g-code header into a routing decision.

Pure functions only — no I/O, no printer contact. Easy to unit-test.
"""
import re
from dataclasses import dataclass


@dataclass
class JobInfo:
    printer: str | None
    printer_model: str = ""
    material: str = ""
    colors: int = 1
    est_seconds: int | None = None
    est_grams: float | None = None


# Substring (lowercased) -> internal printer key. More-specific needles first.
_PRINTER_MAP: list[tuple[str, str]] = [
    ("flashforge ad5x", "ad5x"),
    ("bambu lab a2l", "bambu_a2l"),
    ("bambu lab p1s", "bambu_a2l"),
    ("p1s", "bambu_a2l"),
    ("bambu lab a1 mini", "bambu_a1mini"),
    ("a1 mini", "bambu_a1mini"),
    ("a2l", "bambu_a2l"),
    ("bambu", "bambu"),
    ("ender3 klipper", "ender"),
    ("creality", "ender"),
    ("ender", "ender"),
    ("klipper", "ender"),
]


def _header_value(header: str, key: str) -> str | None:
    """Return the value of a `; key = value` or `; key: value` header line."""
    pat = re.compile(r"^\s*;\s*" + re.escape(key) + r"\s*[:=]\s*(.+?)\s*$")
    for line in header.splitlines():
        m = pat.match(line)
        if m:
            return m.group(1)
    return None


def _material(header: str) -> str:
    raw = _header_value(header, "filament_type") or ""
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    return parts[0] if parts else ""


def _colors(header: str) -> int:
    colour = _header_value(header, "filament_colour")
    if colour:
        return len([c for c in colour.split(";") if c.strip()])
    used = _header_value(header, "filament")
    if used:
        return len([c for c in used.split(",") if c.strip()])
    return 1


def _est_seconds(header: str) -> int | None:
    raw = _header_value(header, "estimated printing time (normal mode)")
    if not raw:
        return None
    total = 0
    matched = False
    for value, unit in re.findall(r"(\d+)\s*([dhms])", raw):
        matched = True
        total += int(value) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
    return total if matched else None


def _est_grams(header: str) -> float | None:
    raw = _header_value(header, "total filament used [g]")
    if not raw:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", raw)
    return float(m.group()) if m else None


def _resolve_printer(model: str, settings_id: str) -> str | None:
    """Match printer_model first; fall back to printer_settings_id when model is blank."""
    for source in (model, settings_id):
        low = source.lower()
        if not low:
            continue
        for needle, key in _PRINTER_MAP:
            if needle in low:
                return key
    return None


def classify(header: str) -> JobInfo:
    model = _header_value(header, "printer_model") or ""
    settings_id = _header_value(header, "printer_settings_id") or ""
    printer = _resolve_printer(model, settings_id)
    return JobInfo(
        printer=printer,
        printer_model=model or settings_id,
        material=_material(header),
        colors=_colors(header),
        est_seconds=_est_seconds(header),
        est_grams=_est_grams(header),
    )
