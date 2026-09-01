"""Fail-closed checks on flattened slicer profiles (REL-602).

A hollow or half-merged process profile used to reach BambuStudio/Orca and
die as ``return -5`` / ``Too small line width``. Catch that in Python with
the missing key names, not a C++ exit code.
"""
from __future__ import annotations

from typing import Any, Iterable, Literal

ProfileRole = Literal["machine", "process", "filament"]

LINE_WIDTH_KEYS = (
    "line_width",
    "initial_layer_line_width",
    "inner_wall_line_width",
    "outer_wall_line_width",
)


class ProfileError(ValueError):
    """Flattened profile is missing identity or required settings."""


def _empty(value: Any) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, (list, tuple)):
        return all(_empty(v) for v in value)
    return False


def ensure_process_line_widths(data: dict[str, Any]) -> dict[str, Any]:
    """Copy ``line_width`` onto any missing specific width keys.

    Flashforge/Orca common profiles often keep one ``line_width`` and leave
    per-feature widths on the parent. If flatten kept the base but dropped
    children, fill them so the C++ slicer does not see 0 and exit -5.
    Missing ``line_width`` itself still raises in :func:`validate_flattened_profile`.
    """
    out = dict(data)
    base = out.get("line_width")
    if _empty(base):
        return out
    for key in LINE_WIDTH_KEYS:
        if key == "line_width":
            continue
        if _empty(out.get(key)):
            out[key] = base
    return out


def validate_flattened_profile(
    data: dict[str, Any],
    *,
    role: ProfileRole,
    requested: str,
) -> None:
    """Raise :class:`ProfileError` if a flattened profile is not sliceable."""
    if not isinstance(data, dict) or not data:
        raise ProfileError(
            f"{role} profile {requested!r} flattened to an empty object — "
            f"refusing to invoke the slicer (this is the REL-602 / -5 path)"
        )

    missing: list[str] = []
    identity = (
        data.get("name")
        or data.get("printer_model")
        or data.get("printer_settings_id")
        or data.get("print_settings_id")
        or data.get("filament_settings_id")
    )
    if _empty(identity):
        missing.append("name/printer_model")
    if _empty(data.get("type")) and _empty(data.get("from")):
        missing.append("type/from")

    if role == "machine":
        if _empty(data.get("printable_area")):
            missing.append("printable_area")
    elif role == "process":
        for key in LINE_WIDTH_KEYS:
            if _empty(data.get(key)):
                missing.append(key)
    elif role == "filament":
        if _empty(data.get("filament_type")) and _empty(data.get("name")):
            missing.append("filament_type")
    else:
        never: Any = role
        raise ProfileError(f"unknown profile role {never!r}")

    if missing:
        chain = data.get("_flattened_from")
        raise ProfileError(
            f"{role} profile {requested!r} is missing {missing} "
            f"(chain={chain}). This used to become a C++ slicer -5 / "
            f"'Too small line width'. Point BAMBU_PROFILES / ORCA_PROFILES at a "
            f"persistent extracted AppImage tree (not /tmp) and re-harvest."
        )


def missing_keys(data: dict[str, Any], keys: Iterable[str]) -> list[str]:
    return [k for k in keys if _empty(data.get(k))]
