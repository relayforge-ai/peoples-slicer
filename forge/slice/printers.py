"""Printer routing table for REL-599 (matches FORGE_CONFIG keys)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Backend = Literal["bambu", "orca"]


@dataclass(frozen=True)
class PrinterSpec:
    """One physical studio machine and how we slice for it."""

    key: str
    display_name: str
    bed_xy_mm: float
    bed_z_mm: float
    backend: Backend
    # Leaf profile names (resolved against the backend's profile tree).
    machine_name: str
    process_name: str
    filament_name: str
    notes: str = ""


# Bed sizes from the REL-599 routing table — these are the fit-check ceilings.
# MMMini in a filename is a *creator* prefix, never a printer (audit trap).
PRINTERS: dict[str, PrinterSpec] = {
    "a1mini": PrinterSpec(
        key="a1mini",
        display_name="Bambu Lab A1 mini",
        bed_xy_mm=180.0,
        bed_z_mm=180.0,
        backend="bambu",
        machine_name="Bambu Lab A1 mini 0.4 nozzle",
        process_name="0.20mm Standard @BBL A1M",
        filament_name="Bambu PLA Basic @BBL A1M",
        notes="plate loader · unattended chainer · single-color today",
    ),
    "a2l": PrinterSpec(
        key="a2l",
        display_name="Bambu Lab P1S (A2L)",
        bed_xy_mm=256.0,
        bed_z_mm=256.0,
        backend="bambu",
        machine_name="Bambu Lab P1S 0.4 nozzle",
        process_name="0.20mm Standard @BBL P1S",
        filament_name="Bambu PLA Basic @BBL P1S",
        notes="AMS 4-color workhorse",
    ),
    "ad5x": PrinterSpec(
        key="ad5x",
        display_name="Flashforge AD5X",
        bed_xy_mm=220.0,
        bed_z_mm=220.0,
        backend="orca",
        machine_name="Flashforge AD5X 0.4 nozzle",
        process_name="0.20mm Standard @FF AD5X",
        filament_name="Flashforge PLA Basic",
        notes="4-color IFS · mandatory for TPU/flex",
    ),
    "ender": PrinterSpec(
        key="ender",
        display_name="Ender 3 (Klipper)",
        bed_xy_mm=235.0,  # Foundry Klipper bed (printer.cfg), not stock 220
        bed_z_mm=250.0,
        backend="orca",
        machine_name="Ender3 Klipper (Foundry)",
        process_name="Foundry 0.20mm Brim",
        filament_name="Silk PLA (Foundry)",
        notes="simple geometry only — vases/fidgets; Klipper-safe wrapper profiles",
    ),
}

# Aliases so agents / Jules don't trip on naming.
# Classifier emits bambu_a1mini / bambu_a2l; the slice table uses a1mini / a2l.
ALIASES = {
    "a1_mini": "a1mini",
    "a1-mini": "a1mini",
    "a1m": "a1mini",
    "bambu_a1_mini": "a1mini",
    "bambu_a1mini": "a1mini",
    "p1s": "a2l",
    "bambu_p1s": "a2l",
    "bambu_a2l": "a2l",
    "flashforge": "ad5x",
    "flashforge_ad5x": "ad5x",
    "ender3": "ender",
    "ender_3": "ender",
}


def get_printer(key: str) -> PrinterSpec:
    """Resolve a printer key (or alias) to a PrinterSpec. Raises KeyError if unknown."""
    k = (key or "").strip().lower()
    k = ALIASES.get(k, k)
    if k not in PRINTERS:
        known = ", ".join(sorted(PRINTERS))
        raise KeyError(f"unknown printer {key!r} (known: {known})")
    return PRINTERS[k]
