"""REL-599 — A1 mini multi-plate batch slicing (Chitu PlateCycler C1M).

Correct model: one multi-plate job with ``plate_change_gcode`` between plates
(Orca PR #13177 style), max 4 plates. Until Ryan supplies verified gcode we still
slice each plate correctly for a1mini and record a batch plan — we never invent
eject moves.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .api import FitError, SliceError, SliceResult, slice_for
from .plate_cycler import MAX_PLATES, PlateChangeNotConfigured, load_plate_change_gcode, plan_batches
from .profile_resolve import write_flattened, bambu_index
from .printers import get_printer
from .routing_ledger import record_fit_failure


@dataclass
class BatchSliceResult:
    printer: str
    models: list[str]
    plates: list[dict[str, Any]] = field(default_factory=list)
    plate_change_configured: bool = False
    plate_change_path: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def inject_plate_change_into_machine(machine_json: Path, gcode: str) -> Path:
    """Write machine settings with plate_change_gcode set (never invents content)."""
    data = json.loads(Path(machine_json).read_text(encoding="utf-8"))
    # Orca/Bambu-style keys used by multi-plate pipelines
    data["plate_change_gcode"] = gcode
    # Some builds look for this between objects on multi-plate jobs
    data["printing_by_object_gcode"] = gcode
    out = machine_json.with_name(machine_json.stem + ".plate_change.json")
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def slice_batch(
    models: list[str | Path],
    *,
    printer: str = "a1mini",
    out_dir: str | Path | None = None,
    auto_refit: bool = True,
    timeout: int = 900,
    dry_run: bool = False,
) -> BatchSliceResult:
    """Slice up to 4 models for the A1 mini cycler (one plate each).

    True single-3mf multi-plate merge depends on plate_change_gcode being configured
    and on BambuStudio accepting multi-file plates. We always produce per-plate
    outputs that are machine-correct for a1mini; when plate_change is present we
    also stamp a batch manifest for the attended merge step.
    """
    spec = get_printer(printer)
    if printer not in {"a1mini", "a1_mini", "a1-mini"}:
        raise ValueError("slice_batch multi-plate cycler is only for a1mini")

    batches = plan_batches(models, printer="a1mini")
    if not batches:
        return BatchSliceResult(printer="a1mini", models=[], notes=["no models"])
    # First batch only for this call (caller loops)
    batch = batches[0]
    out_dir = Path(out_dir or Path.home() / ".forge" / "sliced" / "a1mini_batch")
    out_dir.mkdir(parents=True, exist_ok=True)

    configured = False
    gcode_path = None
    try:
        gcode = load_plate_change_gcode()
        configured = True
        gcode_path = str(
            Path.home() / "print_work" / "multi_slicer" / "plate_change_gcode" / "a1mini_chitu_c1m.gcode"
        )
        # Prefer package default path resolution
        from .plate_cycler import DEFAULT_PLATE_CHANGE_FILE
        if DEFAULT_PLATE_CHANGE_FILE.exists():
            gcode_path = str(DEFAULT_PLATE_CHANGE_FILE)
    except PlateChangeNotConfigured as e:
        gcode = None
        notes_boot = [str(e)]
    else:
        notes_boot = ["plate_change_gcode loaded — stamp into machine for multi-plate merge"]

    result = BatchSliceResult(
        printer="a1mini",
        models=list(batch.models),
        plate_change_configured=configured,
        plate_change_path=gcode_path,
        notes=notes_boot,
    )

    if dry_run:
        result.notes.append(f"dry_run: would slice {len(batch.models)} plates (max {MAX_PLATES})")
        for m in batch.models:
            result.plates.append({"model": m, "status": "planned"})
        return result

    # Optionally pre-build a machine profile with plate_change for operators
    if configured and gcode:
        try:
            idx = bambu_index()
            tmp = Path(tempfile.mkdtemp(prefix="a1mini-plate-"))
            machine = write_flattened(idx, spec.machine_name, tmp / "machine.json")
            stamped = inject_plate_change_into_machine(machine, gcode)
            result.notes.append(f"stamped machine profile: {stamped}")
        except Exception as e:
            result.notes.append(f"could not stamp machine profile: {e}")

    for i, model in enumerate(batch.models, 1):
        dest = out_dir / f"plate_{i:02d}_{Path(model).stem}.gcode.3mf"
        try:
            r: SliceResult = slice_for(
                model,
                "a1mini",
                output=dest,
                timeout=timeout,
                auto_refit=auto_refit,
                goal="photo_line",
            )
            result.plates.append({
                "index": i,
                "model": model,
                "status": "ok",
                "output": r.output,
                "estimates": r.estimates,
                "scale": r.scale,
            })
        except FitError as e:
            bounds = None
            if e.bounds:
                bounds = {"dx": e.bounds.dx, "dy": e.bounds.dy, "dz": e.bounds.dz}
            fact = record_fit_failure(
                model=model, printer="a1mini", message=str(e), bounds=bounds,
            )
            result.plates.append({
                "index": i,
                "model": model,
                "status": "routing_fact",
                "error": str(e),
                "fact": fact,
            })
            result.notes.append(f"plate {i} does not fit — recorded routing fact")
        except (SliceError, FileNotFoundError, Exception) as e:
            result.plates.append({
                "index": i,
                "model": model,
                "status": "failed",
                "error": str(e)[:240],
            })

    manifest = out_dir / "batch_manifest.json"
    manifest.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
    result.notes.append(f"manifest: {manifest}")
    if len(batches) > 1:
        result.notes.append(f"{len(batches) - 1} additional batch(es) remaining (max {MAX_PLATES}/batch)")
    return result
