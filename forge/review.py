"""Deterministic slice-parameter lint — profile rules, zero LLM inference."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .reader import classify_file, read_gcode_meta

# Per-printer finicky-parameter expectations (v0.1 — table-driven, not guessed).
_PROFILES: dict[str, dict] = {
    "ender": {
        "brim_width_min": 5.0,
        "wall_loops_min": 2,
        "nozzle_temp_pla": (200, 235),
        "bed_temp_pla": (55, 70),
        "notes": "Farm truck: brim + manual level; supports often needed on overhangs.",
    },
    "bambu_a2l": {
        "brim_width_min": 0.0,
        "wall_loops_min": 2,
        "nozzle_temp_pla": (210, 240),
        "bed_temp_pla": (50, 65),
        "notes": "AMS multicolor default; verify AMS slot colors match the slice.",
    },
    "bambu_a1mini": {
        "brim_width_min": 0.0,
        "wall_loops_min": 2,
        "nozzle_temp_pla": (210, 240),
        "bed_temp_pla": (50, 65),
        "notes": "Single-tool Bambu; smaller bed than A2L.",
    },
    "bambu": {
        "brim_width_min": 0.0,
        "wall_loops_min": 2,
        "nozzle_temp_pla": (210, 240),
        "bed_temp_pla": (50, 65),
        "notes": "Generic Bambu profile.",
    },
    "ad5x": {
        "brim_width_min": 0.0,
        "wall_loops_min": 2,
        "nozzle_temp_pla": (200, 230),
        "bed_temp_pla": (50, 65),
        "notes": "TPU/flex lane; multicolor needs IFS map at send time.",
    },
}


@dataclass
class Finding:
    param: str
    value: str | float | int | bool | None
    severity: str  # ok | warn | suggest
    message: str


def parse_config_params(meta: str) -> dict[str, str]:
    """Pull `; key = value` lines from a gcode CONFIG block."""
    params: dict[str, str] = {}
    pat = re.compile(r"^\s*;\s*([a-zA-Z0-9_]+)\s*=\s*(.*)\s*$")
    for line in meta.splitlines():
        m = pat.match(line)
        if m:
            params[m.group(1)] = m.group(2).strip()
    return params


def _float_param(params: dict[str, str], key: str) -> float | None:
    raw = params.get(key)
    if raw is None:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", raw)
    return float(m.group()) if m else None


def _int_param(params: dict[str, str], key: str) -> int | None:
    v = _float_param(params, key)
    return int(v) if v is not None else None


def _bool_param(params: dict[str, str], key: str) -> bool | None:
    raw = params.get(key)
    if raw is None:
        return None
    low = raw.lower()
    if low in ("1", "true", "yes", "on"):
        return True
    if low in ("0", "false", "no", "off"):
        return False
    return None


def review_params(params: dict[str, str], printer: str | None, material: str = "") -> list[Finding]:
    profile = _PROFILES.get(printer or "", {})
    findings: list[Finding] = []
    mat = (material or params.get("default_filament_type") or params.get("filament_type") or "").upper()

    brim = _float_param(params, "brim_width")
    brim_min = profile.get("brim_width_min", 0.0)
    if brim is not None:
        if brim >= brim_min:
            findings.append(Finding("brim_width", brim, "ok", f"brim {brim}mm meets profile minimum ({brim_min}mm)"))
        else:
            findings.append(
                Finding(
                    "brim_width",
                    brim,
                    "suggest",
                    f"brim {brim}mm is below profile minimum ({brim_min}mm) — consider re-slicing with a wider brim",
                )
            )

    walls = _int_param(params, "wall_loops")
    wall_min = profile.get("wall_loops_min", 2)
    if walls is not None:
        if walls >= wall_min:
            findings.append(Finding("wall_loops", walls, "ok", f"wall_loops {walls} meets minimum ({wall_min})"))
        else:
            findings.append(
                Finding(
                    "wall_loops",
                    walls,
                    "suggest",
                    f"wall_loops {walls} is thin — profile expects at least {wall_min}",
                )
            )

    supports = _bool_param(params, "enable_support")
    if supports is False:
        findings.append(
            Finding(
                "enable_support",
                False,
                "warn",
                "supports are off — verify overhangs in the Orca preview before sending",
            )
        )
    elif supports is True:
        findings.append(Finding("enable_support", True, "ok", "supports enabled"))

    if "PLA" in mat:
        nozzle = _float_param(params, "nozzle_temperature") or _float_param(params, "temperature")
        bed = _float_param(params, "bed_temperature") or _float_param(params, "curr_bed_type")
        n_range = profile.get("nozzle_temp_pla")
        b_range = profile.get("bed_temp_pla")
        if nozzle is not None and n_range:
            lo, hi = n_range
            if lo <= nozzle <= hi:
                findings.append(Finding("nozzle_temperature", nozzle, "ok", f"nozzle {nozzle}°C in PLA range"))
            else:
                findings.append(
                    Finding(
                        "nozzle_temperature",
                        nozzle,
                        "warn",
                        f"nozzle {nozzle}°C outside expected PLA range ({lo}-{hi}°C) for {printer}",
                    )
                )
        if bed is not None and isinstance(b_range, tuple):
            # bed_temperature may be a plate name; only lint numeric values
            lo, hi = b_range
            if lo <= bed <= hi:
                findings.append(Finding("bed_temperature", bed, "ok", f"bed {bed}°C in PLA range"))

    if "TPU" in mat or "FLEX" in mat:
        if printer not in (None, "ad5x"):
            findings.append(
                Finding(
                    "material_route",
                    mat,
                    "warn",
                    f"flexible material ({mat}) should route to AD5X, not {printer}",
                )
            )
        else:
            findings.append(Finding("material_route", mat, "ok", "flexible material on AD5X"))

    note = profile.get("notes")
    if note:
        findings.append(Finding("profile_note", None, "ok", note))

    return findings


def review_file(path: str, printer: str | None = None) -> dict:
    """Classify one sliced file and lint its parameters against its printer profile.

    ``printer`` overrides the printer the file classifies to; when ``None`` the
    classified printer is used (and an unknown printer falls through to the empty
    profile, yielding only the generic, profile-independent findings).

    Returns the JSON-serializable report that ``forge review`` prints, with keys:

    - ``file`` — the path reviewed.
    - ``printer`` — the profile actually linted against (the override, else the
      classified printer, else ``None``).
    - ``classified_printer`` — what the g-code header alone routes to, kept
      distinct from ``printer`` so an override stays visible.
    - ``material`` / ``colors`` — echoed straight from classification.
    - ``findings`` — a list of ``Finding`` dicts (``param``, ``value``,
      ``severity`` one of ``ok`` / ``warn`` / ``suggest``, ``message``).
    - ``blocking`` — ``True`` when flexible material is routed to the wrong
      printer or a multicolor artifact lacks a verified prime tower. These
      safety findings make ``forge review`` exit non-zero; parameter suggestions
      such as nozzle temperature remain advisory.
    """
    info = classify_file(path)
    target = printer or info.printer
    meta = read_gcode_meta(path)
    params = parse_config_params(meta)
    findings = review_params(params, target, info.material)
    if info.colors > 1:
        tower_ok = info.prime_tower_enabled is True
        findings.append(Finding(
            "enable_prime_tower",
            info.prime_tower_enabled,
            "ok" if tower_ok else "warn",
            (
                "prime tower enabled for multicolor print"
                if tower_ok
                else "multicolor print is blocked until enable_prime_tower = 1"
            ),
        ))
    return {
        "file": path,
        "printer": target,
        "classified_printer": info.printer,
        "material": info.material,
        "colors": info.colors,
        "prime_tower_enabled": info.prime_tower_enabled,
        "findings": [asdict(f) for f in findings],
        "blocking": any(
            f.severity == "warn" and f.param in {"material_route", "enable_prime_tower"}
            for f in findings
        ),
    }
