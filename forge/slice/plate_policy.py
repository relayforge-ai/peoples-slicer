"""REL-600 — agentic plate optimization policy.

Slicer CLIs already expose primitives:
  --scale · --repetitions · --arrange · --orient · multi-file assemble

This module is the **policy layer**: given a model + printer + goal, choose
those knobs. Never invents plate-change gcode (see plate_cycler).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from .fit import model_bounds
from .magnet_plates import MagnetStyle, select_magnet_plate
from .plate_cycler import MAX_PLATES, plan_batches
from .printers import PrinterSpec, get_printer
from .refit import RefitPlan, refit_scale

Goal = Literal["single", "photo_line", "max_parts", "estimate"]

# Until explicit placement exists, mixed-height 3-part plates spaghetti
# (REL-602: Head 44 mm + Fins 26 mm + Tail 18 mm).
MAX_SAME_PLATE_PARTS = 2
MAX_HEIGHT_DELTA_MM = 16.0


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
    slice_plate: int = 1
    plate_label: str = ""
    magnet_style: str = "glue_in"
    extra_models: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def cap_same_plate_models(
    models: list[str | Path],
) -> tuple[list[Path], list[str]]:
    """Keep at most two same-plate parts, and only if heights are similar.

    Captured + glue-in magnet plates must never be passed in here — that is a
    plate-selection problem, not an arrange problem.
    """
    paths = [Path(m) for m in models]
    notes: list[str] = []
    if len(paths) <= 1:
        return paths, notes

    heights: list[tuple[Path, float | None]] = []
    for p in paths:
        b = model_bounds(p)
        heights.append((p, b.dz if b is not None else None))

    if len(paths) > MAX_SAME_PLATE_PARTS:
        notes.append(
            f"capped multi-part plate at {MAX_SAME_PLATE_PARTS} "
            f"(no explicit placement yet; {len(paths)} models given)"
        )
        # Prefer the two closest known heights; unknown heights stay with primary.
        known = [(p, h) for p, h in heights if h is not None]
        if len(known) >= 2:
            best: tuple[Path, Path, float] | None = None
            for i, (p1, h1) in enumerate(known):
                for p2, h2 in known[i + 1 :]:
                    delta = abs(h1 - h2)
                    if best is None or delta < best[2]:
                        best = (p1, p2, delta)
            assert best is not None
            paths = [best[0], best[1]]
            heights = [(p, h) for p, h in heights if p in paths]
        else:
            paths = paths[:MAX_SAME_PLATE_PARTS]
            heights = heights[:MAX_SAME_PLATE_PARTS]

    if len(paths) == 2:
        h1, h2 = heights[0][1], heights[1][1]
        if h1 is not None and h2 is not None and abs(h1 - h2) > MAX_HEIGHT_DELTA_MM:
            notes.append(
                f"refusing mixed-height pair ({h1:.0f} vs {h2:.0f} mm) — "
                f"spaghetti risk; slicing primary only"
            )
            paths = [paths[0]]
    return paths, notes


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
    magnet_style: str | MagnetStyle = "glue_in",
    plate: int | None = None,
) -> PlatePolicy:
    """Choose scale / repetitions / arrange for a model on a studio printer.

    Magnet 3mfs: pick the glue-in / non-captured plate by default. Extra models
    are same-plate STLs, never the other magnet plate.
    """
    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))
    model = Path(model)
    notes: list[str] = []
    multi: list[str] = []
    same_plate: list[str] = []
    slice_plate = 1
    plate_label = ""

    magnet = select_magnet_plate(
        model, style=magnet_style, plate_override=plate
    )
    slice_plate = magnet.slice_plate
    plate_label = magnet.plate_name
    notes.extend(magnet.notes)

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

    if extra_models and magnet.is_magnet_project:
        notes.append(
            "magnet project: extra_models ignored — captured + glue-in are "
            "alternate plates, not a multi-part arrange"
        )
        extra_models = None

    if goal == "estimate":
        # Fast single estimate — no multi-copy
        arrange = 1
        orient = 1
        notes.append("estimate mode: single copy")
    elif goal == "single":
        notes.append("single part on plate")
        if extra_models:
            kept, cap_notes = cap_same_plate_models([model, *extra_models])
            notes.extend(cap_notes)
            same_plate = [str(p) for p in kept[1:]]
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
    else:
        _unknown: Goal = goal
        raise ValueError(f"unknown plate goal {_unknown!r}")

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
        slice_plate=slice_plate,
        plate_label=plate_label,
        magnet_style=str(magnet_style),
        extra_models=same_plate,
    )
