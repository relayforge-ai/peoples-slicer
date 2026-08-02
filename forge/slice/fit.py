"""Per-printer fit checks — reject models that cannot physically print on the bed.

A1 mini is 180×180×180. Sending a 256 mm A1/P1S plate job is not "probably fine" —
start gcode bed-level / purge coordinates off the front of the mini bed = toolhead crash.

.3mf is the main studio format: we bound-box **all** `3D/Objects/*.model` meshes so
fit checks are fail-closed for maker files (not fail-open).
"""
from __future__ import annotations

import json
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .printers import PrinterSpec


@dataclass(frozen=True)
class Bounds:
    dx: float
    dy: float
    dz: float

    @property
    def max_xy(self) -> float:
        return max(self.dx, self.dy)


class FitError(Exception):
    """Model does not fit the target printer bed (routing fact, not a slicer crash)."""

    def __init__(self, message: str, *, bounds: Bounds | None = None, printer: str = ""):
        super().__init__(message)
        self.bounds = bounds
        self.printer = printer


def _bounds_from_stl(path: Path) -> Bounds:
    data = path.read_bytes()
    if len(data) >= 84 and not data[:5].lower().startswith(b"solid"):
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + n * 50 <= len(data) + 50:
            xs: list[float] = []
            ys: list[float] = []
            zs: list[float] = []
            off = 84
            for _ in range(n):
                vals = struct.unpack_from("<12fH", data, off)
                for i in range(3, 12, 3):
                    xs.append(vals[i])
                    ys.append(vals[i + 1])
                    zs.append(vals[i + 2])
                off += 50
            if xs:
                return Bounds(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    text = data.decode("utf-8", "replace")
    coords = [
        tuple(map(float, m.groups()))
        for m in re.finditer(
            r"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", text
        )
    ]
    if not coords:
        raise ValueError(f"could not parse STL bounds: {path}")
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    return Bounds(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


_VERT_RE = re.compile(
    r"""x=["']([-\d.eE+]+)["']\s+y=["']([-\d.eE+]+)["']\s+z=["']([-\d.eE+]+)["']"""
)


def _bounds_from_3mf(path: Path) -> Bounds | None:
    """Union AABB of all object meshes inside a 3mf (studio's primary format)."""
    try:
        with zipfile.ZipFile(path) as z:
            object_models = [
                n for n in z.namelist()
                if n.startswith("3D/Objects/") and n.endswith(".model")
            ]
            # Fall back to single 3dmodel.model
            if not object_models:
                object_models = [
                    n for n in z.namelist()
                    if n.endswith("3dmodel.model") or n.endswith(".model")
                ]
            xs: list[float] = []
            ys: list[float] = []
            zs: list[float] = []
            for name in object_models:
                # Large multicolor parts: stream in chunks would be nicer; full read is OK
                # for studio maker files (typically tens of MB, not hundreds).
                try:
                    raw = z.read(name).decode("utf-8", "replace")
                except Exception:
                    continue
                for m in _VERT_RE.finditer(raw):
                    xs.append(float(m.group(1)))
                    ys.append(float(m.group(2)))
                    zs.append(float(m.group(3)))
            if not xs:
                return None
            return Bounds(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    except (OSError, zipfile.BadZipFile):
        return None


def source_plate_xy_mm(path: Path | str) -> float | None:
    """If the 3mf carries project printable_area, return its XY size (e.g. 256 for P1S)."""
    path = Path(path)
    if path.suffix.lower() != ".3mf":
        return None
    try:
        with zipfile.ZipFile(path) as z:
            if "Metadata/project_settings.config" not in z.namelist():
                return None
            ps = json.loads(z.read("Metadata/project_settings.config"))
            area = ps.get("printable_area")
            if not area or not isinstance(area, list):
                return None
            xs: list[float] = []
            ys: list[float] = []
            for pt in area:
                if not isinstance(pt, str) or "x" not in pt:
                    continue
                a, b = pt.split("x", 1)
                xs.append(float(a))
                ys.append(float(b))
            if not xs:
                return None
            return max(max(xs) - min(xs), max(ys) - min(ys))
    except Exception:
        return None


def model_bounds(path: Path | str) -> Bounds | None:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".stl":
        return _bounds_from_stl(path)
    if suf == ".3mf":
        return _bounds_from_3mf(path)
    return None


def assert_fits(
    path: Path | str,
    printer: PrinterSpec,
    *,
    margin_mm: float = 1.0,
    require_bounds: bool = True,
) -> Bounds | None:
    """Raise FitError if the model exceeds the printer bed (with a small margin).

    When ``require_bounds`` is True (default), unmeasurable .3mf fails closed —
    we refuse to send unknown-size geometry to a smaller bed (crash risk).
    """
    path = Path(path)
    bounds = model_bounds(path)
    if bounds is None:
        if require_bounds and path.suffix.lower() == ".3mf":
            raise FitError(
                f"{path.name}: could not measure mesh bounds in 3mf — refusing "
                f"{printer.display_name} (fail-closed; fix file or pass skip_fit_check)",
                printer=printer.key,
            )
        return None
    limit_xy = printer.bed_xy_mm - margin_mm
    limit_z = printer.bed_z_mm - margin_mm
    if bounds.max_xy > limit_xy or bounds.dz > limit_z:
        raise FitError(
            f"{path.name} is {bounds.dx:.1f}×{bounds.dy:.1f}×{bounds.dz:.1f} mm — "
            f"does not fit {printer.display_name} bed "
            f"{printer.bed_xy_mm:.0f}×{printer.bed_xy_mm:.0f}×{printer.bed_z_mm:.0f} mm "
            f"(routing fact, not a slicer failure)",
            bounds=bounds,
            printer=printer.key,
        )
    return bounds
