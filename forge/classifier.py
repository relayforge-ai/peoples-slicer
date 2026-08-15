"""Classify an OrcaSlicer g-code header into a routing decision.

Pure functions only — no I/O, no printer contact. Easy to unit-test.
"""
import re
from dataclasses import dataclass


@dataclass
class JobInfo:
    """The routing decision distilled from a slice's g-code header.

    This is the data contract the rest of the Forge consumes — the dispatcher
    routes on it, and the CLI/review surfaces echo it back to the user.

    Fields:
        printer: Internal printer key (e.g. ``"ad5x"``, ``"bambu_a2l"``) the job
            should route to, or ``None`` when the header matched no known printer.
        printer_model: The raw human-readable model string from the header
            (``printer_model``, falling back to ``printer_settings_id``); ``""``
            when neither is present. Kept for display/diagnostics, not routing.
        material: Primary filament type, upper- or mixed-case as sliced
            (e.g. ``"PLA"``, ``"TPU"``); ``""`` when the header omits it.
        colors: Number of distinct filaments/colors in the slice (``1`` for a
            single-material job).
        prime_tower_enabled: ``True`` only when the slice explicitly records
            ``enable_prime_tower = 1``; ``False`` when explicitly disabled and
            ``None`` when the setting is absent or unparseable.
        est_seconds: Estimated print time in whole seconds, or ``None`` when the
            header carries no parseable time estimate.
        est_grams: Estimated filament mass in grams, or ``None`` when the header
            carries no parseable mass estimate.
    """

    printer: str | None
    printer_model: str = ""
    material: str = ""
    colors: int = 1
    prime_tower_enabled: bool | None = None
    est_seconds: int | None = None
    est_grams: float | None = None


# Substring (lowercased) -> internal printer key. More-specific needles first.
_PRINTER_MAP: list[tuple[str, str]] = [
    ("flashforge ad5x", "ad5x"),
    ("anycubic kobra 3 max", "kobra3max"),
    ("kobra 3 max", "kobra3max"),
    ("kobra3max", "kobra3max"),
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


def _prime_tower_enabled(header: str) -> bool | None:
    raw = _header_value(header, "enable_prime_tower")
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


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
    """Distill a slice's g-code header text into a routing :class:`JobInfo`.

    The public entry point of this pure-functions module: it takes the already-
    extracted header text (see :func:`forge.reader.classify_file`), does no I/O,
    and never raises on a missing or garbled field — each unresolved field falls
    back to its documented default (``printer`` ``None``, string fields ``""``,
    ``colors`` ``1``, estimates ``None``).

    Printer resolution tries ``printer_model`` first, then ``printer_settings_id``
    as a fallback, matching each against :data:`_PRINTER_MAP` most-specific needle
    first; ``printer`` is ``None`` when neither string matches a known printer.
    ``printer_model`` is echoed back as the raw model string (or the settings id
    when the model line is absent) for display, not routing.
    """
    model = _header_value(header, "printer_model") or ""
    settings_id = _header_value(header, "printer_settings_id") or ""
    printer = _resolve_printer(model, settings_id)
    return JobInfo(
        printer=printer,
        printer_model=model or settings_id,
        material=_material(header),
        colors=_colors(header),
        prime_tower_enabled=_prime_tower_enabled(header),
        est_seconds=_est_seconds(header),
        est_grams=_est_grams(header),
    )
