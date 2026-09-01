"""Magnet 3mf plate selection — glue-in / non-captured by default.

Maker magnet files typically ship TWO plates in one project:
  1. captured / captive (print-in-place around the magnet)
  2. glue-in / non-captured / non-captive / open

Telchar default (2026-09-01): slice the glue-in plate only. Never arrange
captured + glue-in as a multi-part plate. Today's Jules miss
(``pv-flexy-pup-magnet-and-keychain-magnet``) was this class: ``--slice 1``
hit the captured plate.

Catalog pairs like ``pv-mini-cow-magnet-captive`` vs
``pv-mini-cow-magnet-non-captive`` prefer the non-captive file.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET

MagnetStyle = Literal["glue_in", "captured"]

# Longer / negative forms first so "non-captive" is not classified as captive.
_GLUE_RE = re.compile(
    r"(glue[-_ ]?in|non[-_ ]?captur(?:ed|e)|non[-_ ]?captive|\bopen\b|\bglue\b)",
    re.I,
)
_CAPTURED_RE = re.compile(
    r"(print[-_ ]?in[-_ ]?place|\bcaptured\b|\bcaptive\b)",
    re.I,
)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag else tag


def classify_magnet_label(text: str | None) -> MagnetStyle | None:
    """Return ``glue_in``, ``captured``, or ``None`` if the label is unrelated."""
    if not text or not str(text).strip():
        return None
    raw = str(text)
    if _GLUE_RE.search(raw):
        return "glue_in"
    if _CAPTURED_RE.search(raw):
        return "captured"
    return None


def normalize_magnet_style(value: str | None) -> MagnetStyle:
    raw = (value or "glue_in").strip().lower().replace("-", "_")
    if raw in {"glue_in", "gluein", "glue", "non_captured", "noncaptured", "non_captive", "noncaptive", "open"}:
        return "glue_in"
    if raw in {"captured", "captive", "print_in_place", "pip"}:
        return "captured"
    raise ValueError(
        f"unknown magnet style {value!r} — expected glue-in or captured"
    )


@dataclass(frozen=True)
class ProjectPlate:
    index: int  # 1-based slicer ``--slice`` index
    name: str
    object_names: tuple[str, ...] = ()
    kind: MagnetStyle | None = None

    def labels(self) -> str:
        return " ".join(part for part in (self.name, *self.object_names) if part)


@dataclass(frozen=True)
class MagnetPlateDecision:
    """Which plate of a project file to slice, and why."""

    slice_plate: int
    style: MagnetStyle
    plate_name: str
    skipped: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    is_magnet_project: bool = False
    explicit: bool = False


@dataclass
class _PlateAccum:
    index: int
    name: str = ""
    object_ids: list[str] = field(default_factory=list)


def _object_id(elem: ET.Element) -> str:
    return (
        elem.attrib.get("object_id")
        or elem.attrib.get("objectid")
        or elem.attrib.get("id")
        or ""
    )


def _iter_named(root: ET.Element, name: str):
    for elem in root.iter():
        if _local(elem.tag) == name:
            yield elem


def _parse_model_settings(xml_text: str) -> list[ProjectPlate]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    object_names: dict[str, str] = {}
    for obj in _iter_named(root, "object"):
        oid = obj.attrib.get("id") or obj.attrib.get("object_id") or ""
        label = ""
        for meta in obj:
            if _local(meta.tag) == "metadata" and meta.attrib.get("key") == "name":
                label = meta.attrib.get("value") or (meta.text or "")
        if not label:
            label = obj.attrib.get("name") or ""
        if oid and label:
            object_names[str(oid)] = label

    acc: list[_PlateAccum] = []
    for i, plate in enumerate(_iter_named(root, "plate"), start=1):
        meta: dict[str, str] = {}
        obj_ids: list[str] = []
        for child in plate:
            tag = _local(child.tag)
            if tag == "metadata":
                meta[child.attrib.get("key", "")] = child.attrib.get("value", "")
            elif tag in {"model", "object"}:
                oid = _object_id(child)
                if oid:
                    obj_ids.append(oid)
        raw_id = meta.get("plater_id") or meta.get("plate_index") or meta.get("index")
        try:
            index = int(raw_id) if raw_id not in (None, "") else i
        except ValueError:
            index = i
        if index == 0:
            index = 1
        acc.append(
            _PlateAccum(
                index=index,
                name=meta.get("plater_name") or meta.get("name") or meta.get("plate_name") or "",
                object_ids=obj_ids,
            )
        )

    if not acc:
        return []

    # Some files store 0-based plater_id. BambuStudio --slice is 1-based.
    if all(p.index >= 1 for p in acc):
        pass
    elif min(p.index for p in acc) == 0:
        for p in acc:
            p.index += 1

    out: list[ProjectPlate] = []
    for p in acc:
        names = tuple(object_names[oid] for oid in p.object_ids if oid in object_names)
        kind = classify_magnet_label(p.name)
        if kind is None:
            for n in names:
                kind = classify_magnet_label(n)
                if kind is not None:
                    break
        out.append(ProjectPlate(index=p.index, name=p.name, object_names=names, kind=kind))
    return out


def list_project_plates(path: str | Path) -> list[ProjectPlate]:
    """Read plate names/object names from a Bambu/Orca 3mf project."""
    path = Path(path)
    if path.suffix.lower() != ".3mf" and not path.name.lower().endswith(".3mf"):
        return []
    try:
        with zipfile.ZipFile(path) as zf:
            settings = next(
                (
                    n
                    for n in zf.namelist()
                    if n.endswith("model_settings.config") or n.endswith("model_settings.xml")
                ),
                None,
            )
            if settings is None:
                return []
            raw = zf.read(settings).decode("utf-8", "replace")
    except (OSError, zipfile.BadZipFile):
        return []
    return _parse_model_settings(raw)


def prefer_non_captive_path(paths: list[str | Path]) -> Path | None:
    """Among catalog pairs, prefer the non-captive / glue-in filename."""
    if not paths:
        return None
    classified: list[tuple[Path, MagnetStyle | None]] = [
        (Path(p), classify_magnet_label(Path(p).stem)) for p in paths
    ]
    glue = [p for p, k in classified if k == "glue_in"]
    if glue:
        return glue[0]
    unknown = [p for p, k in classified if k is None]
    if unknown:
        return unknown[0]
    return classified[0][0]


class MagnetPlateError(ValueError):
    """Refusing to slice a captured magnet plate under the glue-in default."""


def select_magnet_plate(
    path: str | Path,
    *,
    style: str | MagnetStyle = "glue_in",
    plate_override: int | None = None,
) -> MagnetPlateDecision:
    """Pick the plate Jules should slice.

    * ``style="glue_in"`` (default) — glue-in / non-captured only.
    * ``style="captured"`` — explicit request for the captured plate.
    * ``plate_override`` — explicit 1-based ``--slice`` index (counts as requested).
    """
    path = Path(path)
    wanted = normalize_magnet_style(style)
    plates = list_project_plates(path)
    file_kind = classify_magnet_label(path.stem)

    if plate_override is not None:
        idx = int(plate_override)
        if idx < 1:
            raise MagnetPlateError(f"plate index must be >= 1, got {idx}")
        match = next((p for p in plates if p.index == idx), None)
        name = match.name if match else f"plate {idx}"
        skipped = tuple(
            f"{p.index}:{p.name or p.kind or 'unnamed'}"
            for p in plates
            if p.index != idx
        )
        return MagnetPlateDecision(
            slice_plate=idx,
            style=match.kind or wanted,
            plate_name=name,
            skipped=skipped,
            notes=(f"explicit --plate {idx} ({name})",),
            is_magnet_project=bool(plates) and any(p.kind for p in plates),
            explicit=True,
        )

    magnetish = bool(file_kind) or any(p.kind for p in plates)
    if not magnetish:
        return MagnetPlateDecision(
            slice_plate=1,
            style=wanted,
            plate_name="",
            notes=("not a magnet project — default plate 1",),
            is_magnet_project=False,
        )

    if not plates:
        if file_kind == "captured" and wanted == "glue_in":
            raise MagnetPlateError(
                f"{path.name} looks like a captured-only magnet SKU. "
                f"Telchar default is glue-in / non-captive. Pass --magnet-style captured "
                f"if you really want the print-in-place plate, or slice the "
                f"non-captive / glue-in sibling file."
            )
        return MagnetPlateDecision(
            slice_plate=1,
            style=wanted,
            plate_name=path.stem,
            notes=(f"magnet SKU ({file_kind or wanted}) with no plate list — plate 1",),
            is_magnet_project=True,
        )

    matches = [p for p in plates if p.kind == wanted]
    if matches:
        pick = matches[0]
        skipped = tuple(
            f"{p.index}:{p.name or p.kind or 'unnamed'}"
            for p in plates
            if p.index != pick.index
        )
        ignored = [p for p in plates if p.kind and p.kind != wanted]
        notes = [
            f"magnet default {wanted}: slicing plate {pick.index} "
            f"({pick.name or pick.kind})"
        ]
        if ignored:
            notes.append(
                "ignored "
                + ", ".join(f"plate {p.index} ({p.name or p.kind})" for p in ignored)
                + " — not a multi-part arrange"
            )
        return MagnetPlateDecision(
            slice_plate=pick.index,
            style=wanted,
            plate_name=pick.name or pick.kind or "",
            skipped=skipped,
            notes=tuple(notes),
            is_magnet_project=True,
        )

    if wanted == "glue_in":
        captured = [p for p in plates if p.kind == "captured"]
        raise MagnetPlateError(
            f"{path.name} has no glue-in / non-captured / non-captive / open plate "
            f"(plates: {[(p.index, p.name, p.kind) for p in plates]}). "
            f"Refusing to slice the captured plate by default. "
            f"Pass --magnet-style captured to print-in-place around the magnet."
            + (f" Captured plates: {[p.index for p in captured]}." if captured else "")
        )

    raise MagnetPlateError(
        f"{path.name} has no captured / captive plate to slice "
        f"(plates: {[(p.index, p.name, p.kind) for p in plates]})."
    )
