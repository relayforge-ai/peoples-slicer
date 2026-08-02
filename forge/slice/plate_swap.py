"""Deprecated name — see ``plate_cycler`` (REL-599 correction 2026-08-01).

The Chitu PlateCycler C1M is driven by **plate_change_gcode between plates** of a
merged multi-plate job (Orca PR #13177), **not** machine_end_gcode.

This module remains so older call sites fail with a clear redirect.
"""
from __future__ import annotations

from .plate_cycler import PlateChangeNotConfigured, load_plate_change_gcode


class PlateSwapNotConfigured(PlateChangeNotConfigured):
    """Alias for older imports."""


def plate_swap_end_gcode(*, printer: str = "a1mini", on_success_only: bool = True) -> str:
    """Redirect: use plate_change_gcode via plate_cycler, not end-gcode."""
    if printer not in {"a1mini", "a1_mini", "a1-mini", "a1m"}:
        raise ValueError(f"plate cycler is only for a1mini, not {printer!r}")
    if not on_success_only:
        raise ValueError("plate-change must only run after a successful plate (on_success_only=True)")
    try:
        return load_plate_change_gcode()
    except PlateChangeNotConfigured as e:
        raise PlateSwapNotConfigured(
            f"{e} — also: do NOT append this to machine_end_gcode; use multi-plate plate_change_gcode."
        ) from e
