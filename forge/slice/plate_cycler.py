"""REL-599 — A1 mini Chitu PlateCycler C1M multi-plate batching.

Correct model (2026-08-01 correction):
  * Feeder is **mechanical**, driven by ``plate_change_gcode`` **between plates**
    of one **merged multi-plate job** — NOT an append to machine_end_gcode.
  * Sequence reference: OrcaSlicer PR #13177 (SoftFever).
  * Cap batches at **4 plates** (how many plates ship with the C1M).
  * First cycle is attended; webcam bed-check remains evidence for
    ``bed_confirmed_clear``, not the feeder alone.
  * Skip plate-change on cancel/fail (never shove a half-print into the bin).

Until Ryan verifies the gcode on-hardware, ``load_plate_change_gcode()`` raises
if the verified file is missing — we never invent coordinates.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

MAX_PLATES = 4

# Drop verified gcode here after Ryan's attended first cycle:
#   ~/.forge/plate_change_gcode/a1mini_chitu_c1m.gcode  (or package path below)
DEFAULT_PLATE_CHANGE_FILE = Path(
    os.environ.get(
        "A1MINI_PLATE_CHANGE_GCODE",
        str(Path(__file__).resolve().parent / "plate_change_gcode" / "a1mini_chitu_c1m.gcode"),
    )
)


class PlateChangeNotConfigured(RuntimeError):
    """Verified plate_change_gcode not on disk yet."""


@dataclass
class PlateBatch:
    """One multi-plate job for the A1 mini cycler (≤4 models)."""

    printer: str
    models: list[str] = field(default_factory=list)
    plate_change_gcode_path: str | None = None
    notes: str = ""

    def validate(self) -> None:
        if self.printer not in {"a1mini", "a1_mini", "a1-mini"}:
            raise ValueError("plate cycler batches are only for a1mini")
        if not self.models:
            raise ValueError("batch has no models")
        if len(self.models) > MAX_PLATES:
            raise ValueError(f"batch size {len(self.models)} exceeds MAX_PLATES={MAX_PLATES}")


def load_plate_change_gcode(path: Path | None = None) -> str:
    """Load verified inter-plate gcode, or raise PlateChangeNotConfigured."""
    p = Path(path or DEFAULT_PLATE_CHANGE_FILE)
    if not p.is_file() or p.stat().st_size < 8:
        raise PlateChangeNotConfigured(
            f"A1 mini plate_change_gcode not configured at {p}. "
            "Chitu PlateCycler C1M is multi-plate plate_change_gcode (Orca PR #13177), "
            "NOT machine_end_gcode. Ryan must verify on-hardware after an attended cycle; "
            "never invent eject coordinates."
        )
    text = p.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise PlateChangeNotConfigured(f"empty plate_change_gcode file: {p}")
    return text + ("\n" if not text.endswith("\n") else "")


def plan_batches(models: list[str | Path], *, printer: str = "a1mini") -> list[PlateBatch]:
    """Split a model list into ≤4-plate batches for the cycler."""
    paths = [str(Path(m)) for m in models]
    batches: list[PlateBatch] = []
    gcode_path = None
    try:
        load_plate_change_gcode()
        gcode_path = str(DEFAULT_PLATE_CHANGE_FILE)
    except PlateChangeNotConfigured:
        gcode_path = None
    for i in range(0, len(paths), MAX_PLATES):
        chunk = paths[i : i + MAX_PLATES]
        b = PlateBatch(
            printer=printer,
            models=chunk,
            plate_change_gcode_path=gcode_path,
            notes=(
                "ready for multi-plate merge once plate_change_gcode is verified"
                if gcode_path
                else "blocked: missing verified plate_change_gcode"
            ),
        )
        b.validate()
        batches.append(b)
    return batches
