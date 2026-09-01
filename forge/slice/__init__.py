"""REL-600 / REL-601 — multi-printer headless slice + plate policy for People's Slicer.

Public seam:
  ``slice_for(model, printer)`` — flatten profiles, fit-check, Bambu/Orca backends
  ``plan_plate(...)`` — agentic plate policy (scale / repetitions / arrange)
  ``refit_scale(...)`` — scale the *part* to the bed (not just the plate)
  ``harvest_all()`` — index Orca vendor profile trees

Slicing used to live only under ``~/print_work``; REL-601 lands it in the MIT
``forge`` package so ``forge slice`` / ``forge slice-send`` are first-class.
"""
from .api import FitError, SliceError, SliceResult, slice_for
from .artifact import ArtifactError, assert_sliced_artifact, read_project_settings
from .magnet_plates import (
    MagnetPlateDecision,
    MagnetPlateError,
    ProjectPlate,
    classify_magnet_label,
    list_project_plates,
    prefer_non_captive_path,
    select_magnet_plate,
)
from .plate_cycler import (
    MAX_PLATES,
    PlateBatch,
    PlateChangeNotConfigured,
    load_plate_change_gcode,
    plan_batches,
)
from .plate_policy import MAX_SAME_PLATE_PARTS, PlatePolicy, cap_same_plate_models, plan_plate
from .profile_validate import LINE_WIDTH_KEYS, ProfileError, validate_flattened_profile
from .retarget import (
    clamp_wipe_tower,
    color_count_from_path,
    retarget_models,
    sanitize_project_3mf,
    stamp_target_overrides,
)
from .plate_swap import PlateSwapNotConfigured, plate_swap_end_gcode
from .printers import PRINTERS, PrinterSpec, get_printer
from .profile_harvester import harvest_all, resolve_from_harvest, write_manifest
from .ams_map import map_colors_to_ams
from .multi_plate import BatchSliceResult, inject_plate_change_into_machine, slice_batch
from .refit import RefitPlan, refit_scale
from .routing_ledger import is_known_misfit, record_fit_failure

__all__ = [
    "ArtifactError",
    "BatchSliceResult",
    "FitError",
    "LINE_WIDTH_KEYS",
    "MAX_PLATES",
    "MAX_SAME_PLATE_PARTS",
    "PRINTERS",
    "MagnetPlateDecision",
    "MagnetPlateError",
    "PlateBatch",
    "PlateChangeNotConfigured",
    "PlatePolicy",
    "PlateSwapNotConfigured",
    "PrinterSpec",
    "ProfileError",
    "ProjectPlate",
    "RefitPlan",
    "SliceError",
    "SliceResult",
    "assert_sliced_artifact",
    "cap_same_plate_models",
    "classify_magnet_label",
    "get_printer",
    "harvest_all",
    "inject_plate_change_into_machine",
    "is_known_misfit",
    "list_project_plates",
    "load_plate_change_gcode",
    "map_colors_to_ams",
    "plan_batches",
    "plan_plate",
    "plate_swap_end_gcode",
    "prefer_non_captive_path",
    "read_project_settings",
    "record_fit_failure",
    "refit_scale",
    "resolve_from_harvest",
    "retarget_models",
    "sanitize_project_3mf",
    "stamp_target_overrides",
    "clamp_wipe_tower",
    "color_count_from_path",
    "select_magnet_plate",
    "slice_batch",
    "slice_for",
    "validate_flattened_profile",
    "write_manifest",
]
