"""``slice_for(model, printer)`` — the single multi-printer slicing seam (REL-599)."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backends import build_backend_cmd, run_backend
from .fit import FitError, assert_fits
from .printers import PrinterSpec, get_printer
from .profile_resolve import printable_xy_mm
from .plate_policy import Goal, PlatePolicy, plan_plate
from .refit import RefitPlan, refit_scale


class SliceError(RuntimeError):
    """Slicer process failed or produced no usable output."""


@dataclass
class SliceResult:
    ok: bool
    printer: str
    source: str
    output: str
    backend: str
    bounds: dict[str, float] | None = None
    estimates: dict[str, Any] = field(default_factory=dict)
    flattened_machine: str | None = None
    detail: str = "ok"
    cmd: list[str] = field(default_factory=list)
    scale: float = 1.0
    refit_note: str = ""
    repetitions: int = 1
    policy: dict | None = None


def _estimates_from_3mf(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(path) as z:
            if "Metadata/slice_info.config" in z.namelist():
                info = z.read("Metadata/slice_info.config").decode("utf-8", "replace")
                for key, cast in (("prediction", int), ("weight", float)):
                    m = re.search(rf'<metadata key="{key}" value="([^"]*)"', info)
                    if m and m.group(1):
                        try:
                            out[key] = cast(float(m.group(1)))
                        except ValueError:
                            pass
                if "prediction" in out:
                    out["print_time_min"] = round(out["prediction"] / 60)
            if "Metadata/project_settings.config" in z.namelist():
                try:
                    ps = json.loads(z.read("Metadata/project_settings.config"))
                    for k in (
                        "printer_model",
                        "printer_settings_id",
                        "print_settings_id",
                        "printable_area",
                        "printable_height",
                    ):
                        if k in ps:
                            out[k] = ps[k]
                except (json.JSONDecodeError, TypeError):
                    pass
    except (OSError, zipfile.BadZipFile) as e:
        out["parse_error"] = f"{type(e).__name__}: {e}"
    return out


def _estimates_from_gcode(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return out
    m = re.search(r"estimated printing time[^:]*:\s*([^\n;]+)", text, re.I)
    if m:
        out["estimated_printing_time"] = m.group(1).strip()
    m = re.search(r";\s*printer_model\s*=\s*(.+)", text)
    if m:
        out["printer_model"] = m.group(1).strip()
    return out


def slice_for(
    model: str | Path,
    printer: str | PrinterSpec,
    *,
    output: str | Path | None = None,
    timeout: int = 900,
    skip_fit_check: bool = False,
    dry_run: bool = False,
    auto_refit: bool = False,
    scale: float | None = None,
    goal: Goal | None = None,
    repetitions: int | None = None,
) -> SliceResult:
    """Slice ``model`` for ``printer`` (a1mini | a2l | ad5x | ender).

    * Resolves / flattens machine+process+filament inherits chains.
    * Fit-checks against the routing-table bed size (3mf mesh bounds, fail-closed).
    * Dispatches to BambuStudio or OrcaSlicer with ``--load-settings`` / ``--load-filaments``.
    * ``auto_refit=True`` (REL-600) applies uniform ``--scale`` when the part is oversized.

    A1 mini multi-plate cycler uses ``plate_cycler`` (plate_change_gcode), not end-gcode.
    """
    model_path = Path(model).expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"model not found: {model_path}")

    spec = printer if isinstance(printer, PrinterSpec) else get_printer(str(printer))

    policy: PlatePolicy | None = None
    if goal is not None:
        policy = plan_plate(model_path, spec, goal=goal)
        auto_refit = auto_refit or policy.auto_refit

    refit_plan: RefitPlan | None = None
    applied_scale = 1.0
    applied_reps = 1
    arrange = 1
    orient = 1
    if scale is not None:
        applied_scale = float(scale)
    elif policy is not None:
        applied_scale = policy.scale
        applied_reps = policy.repetitions
        arrange = policy.arrange
        orient = policy.orient
        refit_plan = refit_scale(model_path, spec)
    elif auto_refit:
        refit_plan = refit_scale(model_path, spec)
        applied_scale = refit_plan.scale
    if repetitions is not None:
        applied_reps = max(1, int(repetitions))

    bounds_info = None
    if not skip_fit_check:
        # When auto_refit will scale, check post-scale bounds conceptually.
        try:
            b = assert_fits(model_path, spec)
            if b is not None:
                bounds_info = {"dx": b.dx, "dy": b.dy, "dz": b.dz}
        except FitError:
            if auto_refit or applied_scale < 0.999:
                # Will scale down — re-check after scale
                refit_plan = refit_plan or refit_scale(model_path, spec)
                applied_scale = refit_plan.scale
                if refit_plan.bounds is not None:
                    bounds_info = {
                        "dx": refit_plan.bounds.dx * applied_scale,
                        "dy": refit_plan.bounds.dy * applied_scale,
                        "dz": refit_plan.bounds.dz * applied_scale,
                    }
                if applied_scale >= 0.999:
                    raise
            else:
                raise

    if output is None:
        suffix = ".gcode.3mf" if spec.backend == "bambu" else ".gcode"
        output_path = model_path.with_name(f"{model_path.stem}.{spec.key}{suffix}")
    else:
        output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile_dir = Path(tempfile.mkdtemp(prefix=f"mslice-{spec.key}-"))
    try:
        cmd = build_backend_cmd(
            spec, model_path, output_path,
            profile_dir=profile_dir,
            scale=applied_scale,
            repetitions=applied_reps,
            arrange=arrange,
            orient=orient,
        )

        # Fail-closed machine profile check (REL-631 / zero parameter loss).
        # printable_xy_mm() is None when the profile is empty — the old guard only
        # fired on a *wrong* bed size, so dry-run returned ok=true on blank profiles.
        if not cmd.flattened_machine or not Path(cmd.flattened_machine).is_file():
            raise SliceError(
                f"no machine profile resolved for {spec.key} — check BAMBU_PROFILES / "
                f"ORCA_PROFILES (or FOUNDRY_ORCA_PROFILES) point at a real, extracted "
                f"slicer profile tree"
            )
        flat = json.loads(Path(cmd.flattened_machine).read_text(encoding="utf-8"))
        xy = printable_xy_mm(flat)
        if xy is None:
            raise SliceError(
                f"flattened machine profile for {spec.key} has no printable_area — "
                f"empty or incomplete profile (refusing ok=true dry-run) "
                f"({cmd.flattened_machine})"
            )
        if abs(xy - spec.bed_xy_mm) > 5:
            raise SliceError(
                f"flattened machine bed XY={xy} does not match {spec.key} "
                f"{spec.bed_xy_mm} — inherits chain not applied correctly"
            )
        if not flat.get("printer_model") and not flat.get("name"):
            raise SliceError(
                f"flattened machine missing printer_model/name for {spec.key}"
            )


        if dry_run:
            return SliceResult(
                ok=True,
                printer=spec.key,
                source=str(model_path),
                output=str(output_path),
                backend=spec.backend,
                bounds=bounds_info,
                flattened_machine=str(cmd.flattened_machine) if cmd.flattened_machine else None,
                detail="dry_run",
                cmd=cmd.argv,
                scale=applied_scale,
                refit_note=(refit_plan.note if refit_plan else (policy.notes[0] if policy and policy.notes else "")),
                repetitions=applied_reps,
                policy=policy.as_dict() if policy else None,
            )

        # Clean stale output so we never treat a previous file as success.
        if output_path.exists():
            output_path.unlink()

        proc = run_backend(cmd, timeout=timeout)

        # Orca writes plate_1.gcode into outputdir; normalize to requested path.
        if spec.backend == "orca" and not output_path.exists():
            candidates = sorted(output_path.parent.glob("*.gcode"))
            # Prefer plate_*.gcode from this run
            plates = [p for p in candidates if p.name.startswith("plate_")]
            pick = plates[0] if plates else (candidates[0] if candidates else None)
            if pick and pick.resolve() != output_path.resolve():
                shutil.move(str(pick), str(output_path))

        if not output_path.exists() or output_path.stat().st_size <= 0:
            err = (proc.stdout or "") + (proc.stderr or "")
            tail = "\n".join(err.splitlines()[-12:])
            raise SliceError(
                f"slice failed for {spec.key} (rc={proc.returncode}): {tail or 'no output'}"
            )

        estimates: dict[str, Any] = {}
        if output_path.suffix == ".3mf" or output_path.name.endswith(".gcode.3mf"):
            estimates = _estimates_from_3mf(output_path)
        elif output_path.suffix == ".gcode":
            estimates = _estimates_from_gcode(output_path)

        return SliceResult(
            ok=True,
            printer=spec.key,
            source=str(model_path),
            output=str(output_path),
            backend=spec.backend,
            bounds=bounds_info,
            estimates=estimates,
            flattened_machine=str(cmd.flattened_machine) if cmd.flattened_machine else None,
            detail="ok",
            cmd=cmd.argv,
            scale=applied_scale,
            refit_note=(refit_plan.note if refit_plan else (policy.notes[0] if policy and policy.notes else "")),
            repetitions=applied_reps,
            policy=policy.as_dict() if policy else None,
        )
    finally:
        # Keep profile dir when MULTI_SLICER_KEEP_PROFILES=1 for debugging.
        import os
        if os.environ.get("MULTI_SLICER_KEEP_PROFILES") != "1":
            shutil.rmtree(profile_dir, ignore_errors=True)
