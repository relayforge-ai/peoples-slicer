"""REL-600 — ``refit(model, printer)``: scale geometry so it fits the target bed.

Orca/Bambu can change the *plate* without resizing the *part*. We compute a uniform
scale factor from measured mesh bounds and pass ``--scale`` into the slicer CLI.

XXL skeleton on A2L is the ideal fixture (Ryan); a1mini is the strictest bed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fit import Bounds, model_bounds
from .printers import PrinterSpec, get_printer


@dataclass(frozen=True)
class RefitPlan:
    printer: str
    bounds: Bounds | None
    scale: float
    fits_without_scale: bool
    bed_xy_mm: float
    bed_z_mm: float
    note: str = ""


def refit_scale(
    model: str | Path,
    printer: str | PrinterSpec,
    *,
    margin_mm: float = 2.0,
    max_scale: float = 1.0,
    min_scale: float = 0.15,
) -> RefitPlan:
    """Return a uniform scale ≤1 that places the model inside the printer bed.

    Does not write files — pure plan. ``max_scale`` defaults to 1 (never enlarge).
    """
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    bounds = model_bounds(model)
    if bounds is None:
        return RefitPlan(
            printer=spec.key,
            bounds=None,
            scale=1.0,
            fits_without_scale=False,
            bed_xy_mm=spec.bed_xy_mm,
            bed_z_mm=spec.bed_z_mm,
            note="bounds unknown — no auto-scale; slice may still fail fit check",
        )
    limit_xy = max(1.0, spec.bed_xy_mm - margin_mm)
    limit_z = max(1.0, spec.bed_z_mm - margin_mm)
    sx = limit_xy / bounds.max_xy if bounds.max_xy > 0 else 1.0
    sz = limit_z / bounds.dz if bounds.dz > 0 else 1.0
    raw = min(sx, sz, max_scale)
    if raw >= 0.999:
        return RefitPlan(
            printer=spec.key,
            bounds=bounds,
            scale=1.0,
            fits_without_scale=True,
            bed_xy_mm=spec.bed_xy_mm,
            bed_z_mm=spec.bed_z_mm,
            note="fits at 1:1",
        )
    scale = max(min_scale, raw)
    return RefitPlan(
        printer=spec.key,
        bounds=bounds,
        scale=round(scale, 4),
        fits_without_scale=False,
        bed_xy_mm=spec.bed_xy_mm,
        bed_z_mm=spec.bed_z_mm,
        note=(
            f"scale {scale:.3f}× so "
            f"{bounds.dx:.1f}×{bounds.dy:.1f}×{bounds.dz:.1f} mm fits "
            f"{spec.bed_xy_mm:.0f}³ bed"
        ),
    )
