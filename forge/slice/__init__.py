"""REL-600 / REL-601 — multi-printer headless slice + plate policy for Telchar's Forge.

Public seam:
  ``slice_for(model, printer)`` — flatten profiles, fit-check, Bambu/Orca backends
  ``plan_plate(...)`` — agentic plate policy (scale / repetitions / arrange)
  ``refit_scale(...)`` — scale the *part* to the bed (not just the plate)
  ``harvest_all()`` — index Orca vendor profile trees

Slicing used to live only under ``~/print_work``; REL-601 lands it in the MIT
``forge`` package so ``forge slice`` / ``forge slice-send`` are first-class.
"""
from .api import FitError, SliceError, SliceResult, slice_for
from .plate_cycler import (
    MAX_PLATES,
    PlateBatch,
    PlateChangeNotConfigured,
    load_plate_change_gcode,
    plan_batches,
)
from .plate_policy import PlatePolicy, plan_plate
from .plate_swap import PlateSwapNotConfigured, plate_swap_end_gcode
from .printers import PRINTERS, PrinterSpec, get_printer
from .profile_harvester import harvest_all, resolve_from_harvest, write_manifest
from .refit import RefitPlan, refit_scale

__all__ = [
    "FitError",
    "MAX_PLATES",
    "PRINTERS",
    "PlateBatch",
    "PlateChangeNotConfigured",
    "PlatePolicy",
    "PlateSwapNotConfigured",
    "PrinterSpec",
    "RefitPlan",
    "SliceError",
    "SliceResult",
    "get_printer",
    "harvest_all",
    "load_plate_change_gcode",
    "plan_batches",
    "plan_plate",
    "plate_swap_end_gcode",
    "refit_scale",
    "resolve_from_harvest",
    "slice_for",
    "write_manifest",
]
