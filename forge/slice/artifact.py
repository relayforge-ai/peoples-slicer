"""Assert on sliced artifacts — the check that would have caught REL-602.

Green return codes and mocks said the A1 mini / AD5X paths were fine while
real plates were empty, the wrong ``printer_model``, or a 256 mm bed on a
180 mm machine. Always read ``Metadata/project_settings.config`` (or the
gcode header) and compare ``printer_model`` + ``printable_area``.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .printers import get_printer
from .profile_resolve import printable_xy_mm
from .retarget import (
    color_count_from_settings,
    prime_tower_enabled,
    wipe_tower_inside_bed,
)

# Expected identity after a real slice (REL-599 / REL-602).
EXPECTED_PRINTER_MODEL = {
    "a1mini": "Bambu Lab A1 mini",
    "a2l": "Bambu Lab P1S",
    "ad5x": "Flashforge AD5X",
    "ender": "Ender",
}


class ArtifactError(AssertionError):
    """Sliced output does not match the target printer."""


def read_project_settings(path: str | Path) -> dict[str, Any]:
    """Return project_settings from a .gcode.3mf, or header-derived keys from .gcode."""
    path = Path(path)
    if path.suffix.lower() == ".3mf" or path.name.endswith(".gcode.3mf"):
        with zipfile.ZipFile(path) as zf:
            if "Metadata/project_settings.config" not in zf.namelist():
                raise ArtifactError(
                    f"{path.name} has no Metadata/project_settings.config — "
                    f"empty/wrong artifact (the A1 mini /tmp-profile failure mode)"
                )
            raw = zf.read("Metadata/project_settings.config")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ArtifactError(
                    f"{path.name} project_settings.config is not JSON: {exc}"
                ) from exc
            if not isinstance(data, dict) or not data:
                raise ArtifactError(
                    f"{path.name} project_settings.config is empty — refusing to treat as sliced"
                )
            return data
    text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    out: dict[str, Any] = {}
    for key in (
        "printer_model",
        "printer_settings_id",
        "printable_area",
        "printable_height",
    ):
        m = re.search(rf";\s*{re.escape(key)}\s*=\s*(.+)", text)
        if m:
            val = m.group(1).strip()
            if key == "printable_area" and ";" in val:
                out[key] = [p.strip() for p in val.split(";") if p.strip()]
            else:
                out[key] = val
    return out


def area_xy_mm(area: Any) -> float | None:
    if isinstance(area, (int, float)):
        return float(area)
    if isinstance(area, str) and "x" in area and not area[0].isdigit():
        return None
    if isinstance(area, str):
        # "180x180" or a single polygon point
        parts = area.replace(" ", "").split("x")
        try:
            nums = [float(p) for p in parts if p]
        except ValueError:
            return None
        if len(nums) >= 2:
            return max(nums[0], nums[1])
        return None
    return printable_xy_mm({"printable_area": area})


def assert_sliced_artifact(path: str | Path, printer: str) -> dict[str, Any]:
    """Assert the output file is really sliced for ``printer``.

    This is the REL-602 contract::

        cfg["printer_model"] matches the studio machine
        cfg["printable_area"] XY matches the routing-table bed
        multicolor requires enable_prime_tower = 1 (every printer)
        wipe_tower_x/y stay inside the destination bed
    """
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise ArtifactError(f"sliced artifact missing or empty: {path}")

    spec = get_printer(printer)
    cfg = read_project_settings(path)
    _enrich_from_gcode_header(cfg, path)
    model = str(cfg.get("printer_model") or cfg.get("printer_settings_id") or "")
    expected = EXPECTED_PRINTER_MODEL[spec.key]
    if expected.lower() not in model.lower():
        raise ArtifactError(
            f"{path.name} printer_model={model!r} does not contain {expected!r} "
            f"(would have crashed a {spec.display_name} or printed the wrong bed)"
        )

    xy = area_xy_mm(cfg.get("printable_area"))
    if xy is None:
        raise ArtifactError(
            f"{path.name} has no printable_area — empty flatten / wrong plate"
        )
    if abs(xy - spec.bed_xy_mm) > 5:
        raise ArtifactError(
            f"{path.name} printable_area XY={xy} does not match {spec.key} "
            f"{spec.bed_xy_mm} mm bed — 256 mm gcode on the A1 mini is a toolhead crash"
        )

    colors = color_count_from_settings(cfg)
    if colors > 1 and prime_tower_enabled(cfg.get("enable_prime_tower")) is not True:
        raise ArtifactError(
            "REL-602 output validation failed: multicolor slice requires "
            "enable_prime_tower = 1 on every printer — refusing artifact "
            "and requesting a corrected/manual slice"
        )
    if colors > 1 and not wipe_tower_inside_bed(cfg, spec.bed_xy_mm):
        raise ArtifactError(
            f"REL-602 output validation failed: wipe_tower_x/y "
            f"({cfg.get('wipe_tower_x')!r},{cfg.get('wipe_tower_y')!r}) "
            f"is outside the {spec.bed_xy_mm:.0f} mm bed — refusing artifact"
        )
    return cfg


def _enrich_from_gcode_header(cfg: dict[str, Any], path: Path) -> None:
    """Fill prime-tower / colour keys from plate gcode when project_settings omits them."""
    if path.suffix.lower() != ".3mf" and not path.name.endswith(".gcode.3mf"):
        return
    try:
        with zipfile.ZipFile(path) as zf:
            gc_name = next((n for n in zf.namelist() if n.endswith("plate_1.gcode")), None)
            if gc_name is None:
                return
            text = zf.read(gc_name).decode("utf-8", "replace")[:80_000]
    except (OSError, zipfile.BadZipFile):
        return
    for key in ("enable_prime_tower", "filament_colour", "wipe_tower_x", "wipe_tower_y"):
        if cfg.get(key) not in (None, ""):
            continue
        m = re.search(rf";\s*{re.escape(key)}\s*=\s*(.+)", text)
        if m:
            cfg[key] = m.group(1).strip()
