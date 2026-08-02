"""REL-600 — agentic plate optimization policy.

Slicer CLIs already expose primitives:
  --scale · --repetitions · --arrange · --orient · multi-file assemble

This module is the **policy layer**: given a model + printer + goal, choose
those knobs. Never invents plate-change gcode (see plate_cycler).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .fit import model_bounds
from .plate_cycler import MAX_PLATES, plan_batches
from .printers import PrinterSpec, get_printer
from .refit import RefitPlan, refit_scale

Goal = Literal["single", "photo_line", "max_parts", "estimate"]


@dataclass(frozen=True)
class PlatePolicy:
    """Resolved slicer knobs for one job."""

    printer: str
    goal: str
    scale: float
    repetitions: int
    arrange: int  # 0 disable, 1 enable
    orient: int   # 0 disable, 1 enable
    auto_refit: bool
    multi_plate_models: list[str]
    notes: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def _parts_per_plate(bounds_xy: float, bed_xy: float, *, margin: float = 4.0, gap: float = 3.0) -> int:
    """How many copies of a square footprint fit on the bed (axis-aligned grid)."""
    if bounds_xy <= 0:
        return 1
    cell = bounds_xy + gap
    usable = bed_xy - margin
    n = max(1, int(usable // cell))
    return max(1, n * n)


def plan_plate(
    model: str | Path,
    printer: str | PrinterSpec,
    *,
    goal: Goal = "single",
    extra_models: list[str | Path] | None = None,
    max_repetitions: int = 16,
) -> PlatePolicy:
    """Choose scale / repetitions / arrange for a model on a studio printer."""
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    model = Path(model)
    notes: list[str] = []
    multi: list[str] = []

    refit: RefitPlan = refit_scale(model, spec)
    scale = refit.scale
    if not refit.fits_without_scale:
        notes.append(refit.note)

    bounds = refit.bounds or model_bounds(model)
    bounds_xy = bounds.max_xy * scale if bounds else 0.0

    repetitions = 1
    arrange = 1
    orient = 1
    auto_refit = scale < 0.999

    if goal == "estimate":
        # Fast single estimate — no multi-copy
        arrange = 1
        orient = 1
        notes.append("estimate mode: single copy")
    elif goal == "single":
        notes.append("single part on plate")
    elif goal == "max_parts":
        if bounds_xy > 0:
            n = _parts_per_plate(bounds_xy, spec.bed_xy_mm)
            repetitions = min(max_repetitions, n)
            notes.append(f"max_parts: {repetitions} copies (~{bounds_xy:.1f} mm footprint on {spec.bed_xy_mm:.0f} bed)")
        else:
            notes.append("max_parts: bounds unknown — defaulting to 1 copy")
    elif goal == "photo_line":
        # Catalog photo production: prefer short single prints; batch via plate cycler
        # for a1mini when multiple models are queued.
        notes.append("photo_line: single part per plate; use cycler for multi-SKU batches")
        if extra_models and spec.key == "a1mini":
            paths = [str(model)] + [str(p) for p in extra_models]
            batches = plan_batches(paths, printer="a1mini")
            multi = batches[0].models if batches else [str(model)]
            notes.append(
                f"photo_line batch: {len(multi)}/{MAX_PLATES} plates planned "
                f"({len(batches)} batch(es) total)"
            )
        elif extra_models:
            notes.append("photo_line multi-SKU on non-a1mini: sequential singles (no cycler)")

    return PlatePolicy(
        printer=spec.key,
        goal=goal,
        scale=scale,
        repetitions=repetitions,
        arrange=arrange,
        orient=orient,
        auto_refit=auto_refit,
        multi_plate_models=multi,
        notes=notes,
    )
