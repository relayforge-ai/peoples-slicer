"""Retarget a maker 3mf so project-file keys cannot beat the destination printer.

Verified on Dawes 2026-09-01 (fill-20260901-a1mini-flexypup): a Printverse
Kobra Max 3mf (5 colours, 400 mm bed, ``enable_prime_tower=0``,
``wipe_tower_y=220``) was opened in BambuStudio with ``--load-settings`` for
the A1 mini. The CLI rewrote ``printer_model`` / ``print_settings_id`` but
**left the source process keys in place**. REL-602 correctly refused the
artifact. The flatten already had ``enable_prime_tower=1`` — the 3mf overrode
it.

Target printer wins for:
  * ``enable_prime_tower`` — must be 1 when colour count > 1
  * ``printable_area`` / ``printable_height`` / ``printer_model``
  * ``wipe_tower_x`` / ``wipe_tower_y`` — clamped inside the destination bed
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from .printers import PrinterSpec, get_printer
from .profile_resolve import printable_xy_mm

# Keys the source 3mf must not be allowed to keep when they fight the target.
_SETTINGS_MARKERS = (
    "enable_prime_tower",
    "wipe_tower_x",
    "wipe_tower_y",
    "printable_area",
    "filament_colour",
    "printer_model",
)

DEFAULT_TOWER_WIDTH_MM = 35.0
TOWER_MARGIN_MM = 8.0


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        return _as_float(value[0]) if value else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num_setting(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def prime_tower_enabled(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        return prime_tower_enabled(value[0]) if value else None
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def color_count_from_settings(data: dict[str, Any]) -> int:
    colour = data.get("filament_colour") or data.get("filament_color")
    if isinstance(colour, list):
        parts = [str(c).strip() for c in colour if str(c).strip()]
        return max(1, len(parts))
    if isinstance(colour, str) and colour.strip():
        parts = [c.strip() for c in colour.split(";") if c.strip()]
        return max(1, len(parts))
    used = data.get("filament")
    if isinstance(used, str) and used.strip():
        parts = [c.strip() for c in used.split(",") if c.strip()]
        if parts:
            return max(1, len(parts))
    return 1


def read_embedded_project_settings(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if path.suffix.lower() != ".3mf" and not path.name.lower().endswith(".3mf"):
        return None
    try:
        with zipfile.ZipFile(path) as zf:
            name = next(
                (n for n in zf.namelist() if n.endswith("project_settings.config")),
                None,
            )
            if name is None:
                return None
            raw = zf.read(name)
    except (OSError, zipfile.BadZipFile):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def color_count_from_path(path: str | Path) -> int:
    settings = read_embedded_project_settings(path)
    if settings:
        return color_count_from_settings(settings)
    return 1


def clamp_wipe_tower(
    x: float | None,
    y: float | None,
    *,
    bed_xy_mm: float,
    width_mm: float = DEFAULT_TOWER_WIDTH_MM,
    margin_mm: float = TOWER_MARGIN_MM,
) -> tuple[float, float]:
    """Keep the wipe/prime tower fully on the destination bed."""
    width = max(1.0, width_mm)
    margin = max(0.0, margin_mm)
    max_pos = max(margin, bed_xy_mm - width - margin)
    if x is None:
        x = max_pos
    if y is None:
        y = max_pos
    return (
        min(max(x, margin), max_pos),
        min(max(y, margin), max_pos),
    )


def _area_for_spec(spec: PrinterSpec, machine: dict[str, Any] | None) -> list[str]:
    if machine:
        area = machine.get("printable_area")
        if isinstance(area, list) and area:
            return list(area)
    bed = spec.bed_xy_mm
    n = _num_setting(bed)
    return ["0x0", f"{n}x0", f"{n}x{n}", f"0x{n}"]


def stamp_target_overrides(
    settings: dict[str, Any],
    printer: str | PrinterSpec,
    *,
    colors: int,
    machine: dict[str, Any] | None = None,
    process: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return *settings* with destination-printer keys forced (source cannot win)."""
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    out = dict(settings)
    machine = machine or {}
    process = process or {}

    out["printable_area"] = _area_for_spec(spec, machine)
    height = machine.get("printable_height") or spec.bed_z_mm
    out["printable_height"] = height if isinstance(height, str) else _num_setting(float(height))
    out["printer_model"] = machine.get("printer_model") or spec.display_name
    if machine.get("name"):
        out["printer_settings_id"] = machine["name"]
    if process.get("name"):
        out["print_settings_id"] = process["name"]

    if colors > 1:
        out["enable_prime_tower"] = "1"

    width = (
        _as_float(out.get("prime_tower_width"))
        or _as_float(out.get("wipe_tower_width"))
        or _as_float(process.get("prime_tower_width"))
        or DEFAULT_TOWER_WIDTH_MM
    )
    x, y = clamp_wipe_tower(
        _as_float(out.get("wipe_tower_x")),
        _as_float(out.get("wipe_tower_y")),
        bed_xy_mm=spec.bed_xy_mm,
        width_mm=width,
    )
    out["wipe_tower_x"] = _num_setting(x)
    out["wipe_tower_y"] = _num_setting(y)
    return out


def _looks_like_settings(name: str, data: dict[str, Any]) -> bool:
    if not any(name.endswith(s) for s in ("project_settings.config", ".json", "process_settings.config")):
        return False
    return any(k in data for k in _SETTINGS_MARKERS)


def sanitize_project_3mf(
    src: str | Path,
    dest: str | Path,
    printer: str | PrinterSpec,
    *,
    colors: int | None = None,
    machine: dict[str, Any] | None = None,
    process: dict[str, Any] | None = None,
) -> Path:
    """Copy *src* 3mf with target-printer keys stamped over project settings."""
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    if colors is None:
        colors = color_count_from_path(src)

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dest, "w") as zout:
        for info in zin.infolist():
            blob = zin.read(info.filename)
            if info.filename.endswith(".json") or info.filename.endswith(".config"):
                try:
                    parsed = json.loads(blob)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict) and _looks_like_settings(info.filename, parsed):
                    stamped = stamp_target_overrides(
                        parsed, spec, colors=colors, machine=machine, process=process
                    )
                    blob = (json.dumps(stamped, indent=2) + "\n").encode("utf-8")
            zout.writestr(info, blob)
    return dest


def retarget_models(
    models: list[Path],
    printer: str | PrinterSpec,
    *,
    dest_dir: Path,
    machine: dict[str, Any],
    process: dict[str, Any],
) -> tuple[list[Path], dict[str, Any], int]:
    """Sanitize maker 3mfs and stamp the flattened process for the target printer.

    Returns ``(models_for_cli, stamped_process, color_count)``.
    """
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    colors = max((color_count_from_path(m) for m in models), default=1)
    stamped_process = stamp_target_overrides(
        process, spec, colors=colors, machine=machine, process=process
    )
    out: list[Path] = []
    for model in models:
        settings = read_embedded_project_settings(model)
        if settings is None:
            out.append(model)
            continue
        dest = dest_dir / f"retarget_{model.name}"
        sanitize_project_3mf(
            model,
            dest,
            spec,
            colors=color_count_from_settings(settings),
            machine=machine,
            process=stamped_process,
        )
        out.append(dest)
    return out, stamped_process, colors


def wipe_tower_inside_bed(
    settings: dict[str, Any],
    bed_xy_mm: float,
    *,
    width_mm: float | None = None,
) -> bool:
    """True when wipe_tower_x/y exist and the tower footprint stays on the bed."""
    x = _as_float(settings.get("wipe_tower_x"))
    y = _as_float(settings.get("wipe_tower_y"))
    if x is None or y is None:
        return False
    width = width_mm or _as_float(settings.get("prime_tower_width")) or DEFAULT_TOWER_WIDTH_MM
    if x < 0 or y < 0:
        return False
    if x > bed_xy_mm or y > bed_xy_mm:
        return False
    if x + width > bed_xy_mm + 0.5 or y + width > bed_xy_mm + 0.5:
        return False
    return True


def bed_xy_from_settings(settings: dict[str, Any]) -> float | None:
    return printable_xy_mm(settings)
