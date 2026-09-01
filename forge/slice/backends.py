"""Slicer backends: BambuStudio (a1mini, a2l) and OrcaSlicer (ad5x, ender)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .printers import PrinterSpec
from .profile_resolve import (
    DEFAULT_FOUNDRY_ORCA,
    bambu_index,
    orca_index,
    write_flattened,
)


def _bambu_bin() -> Path:
    return Path(os.environ.get(
        "BAMBU_STUDIO_BIN",
        str(Path.home() / "Desktop" / "BambuStudio_ubuntu24.04_v02.07.01.62.AppImage"),
    ))


def _orca_root() -> Path:
    return Path(os.environ.get(
        "ORCA_ROOT",
        str(Path.home() / "orcaslicer" / "squashfs-root"),
    ))


def _orca_lib_path(root: Path) -> str:
    dirs = sorted({str(p.parent) for p in root.rglob("*.so*")})
    return ":".join(dirs)


@dataclass
class BackendCmd:
    argv: list[str]
    env: dict[str, str]
    workdir: Path | None = None
    flattened_machine: Path | None = None
    flattened_process: Path | None = None
    flattened_filament: Path | None = None


def _as_model_list(model: Path | Sequence[Path]) -> list[Path]:
    if isinstance(model, (str, Path)):
        return [Path(model)]
    paths = [Path(m) for m in model]
    if not paths:
        raise ValueError("build_backend_cmd requires at least one model")
    return paths


def build_backend_cmd(
    printer: PrinterSpec,
    model: Path | Sequence[Path],
    output: Path,
    *,
    profile_dir: Path | None = None,
    scale: float = 1.0,
    repetitions: int = 1,
    arrange: int = 1,
    orient: int = 1,
    slice_plate: int | None = None,
) -> BackendCmd:
    """Build the headless CLI for this printer (does not execute).

    ``model`` may be one path or several — BambuStudio / Orca accept multiple
    trailing model args on one plate (REL-602). Magnet captured+glue-in plates
    must never arrive here as a pair; ``slice_for`` filters those first.
    """
    models = _as_model_list(model)
    output = Path(output)
    tmp = Path(profile_dir or tempfile.mkdtemp(prefix=f"mslice-{printer.key}-"))
    tmp.mkdir(parents=True, exist_ok=True)
    scale = float(scale) if scale and scale > 0 else 1.0
    repetitions = max(1, int(repetitions or 1))
    arrange = 0 if arrange == 0 else 1
    orient = 0 if orient == 0 else 1

    if printer.backend == "bambu":
        idx = bambu_index()
        machine = write_flattened(idx, printer.machine_name, tmp / "machine.json", role="machine")
        process = write_flattened(idx, printer.process_name, tmp / "process.json", role="process")
        filament = write_flattened(idx, printer.filament_name, tmp / "filament.json", role="filament")
        bs = _bambu_bin()
        plate = 1 if slice_plate is None else int(slice_plate)
        # BambuStudio: --slice N is 1-based plate index; load-settings = machine;process
        argv = [
            "xvfb-run", "-a", str(bs),
            "--load-settings", f"{machine};{process}",
            "--load-filaments", str(filament),
        ]
        if abs(scale - 1.0) > 1e-6:
            argv.extend(["--scale", str(scale)])
        if repetitions > 1:
            argv.extend(["--repetitions", str(repetitions)])
        argv.extend(["--arrange", str(arrange), "--orient", str(orient)])
        argv.extend([
            "--slice", str(plate),
            "--export-3mf", str(output),
            *[str(m) for m in models],
        ])
        return BackendCmd(
            argv=argv,
            env=os.environ.copy(),
            flattened_machine=machine,
            flattened_process=process,
            flattened_filament=filament,
        )

    if printer.backend == "orca":
        idx = orca_index()

        def _resolve_or_foundry_fallback(
            name: str, fallback: Path, dest: Path, *, role: str
        ) -> Path:
            # Ender Foundry profiles live outside the AppImage tree and already inherit
            # stock Creality names; flatten when possible, else pass through the Foundry
            # leaf file — but only if that fallback actually exists. REL-631: silently
            # handing back a nonexistent fallback path recreates the same fail-open the
            # missing-vendor-profile case has: `cmd.flattened_machine` gets set to a Path
            # that was never validated, and downstream code only checks it when the path
            # happens to exist (`if cmd.flattened_machine and cmd.flattened_machine.exists()`)
            # — a nonexistent fallback would skip that check entirely instead of failing.
            try:
                return write_flattened(idx, name, dest, role=role)
            except FileNotFoundError as exc:
                if fallback.exists():
                    return fallback
                raise FileNotFoundError(
                    f"profile not found: {name!r}, and the Foundry fallback {fallback} "
                    f"does not exist either. Set ORCA_PROFILES to an extracted Orca/"
                    f"Orca-Flashforge AppImage's resources/profiles directory, or "
                    f"FOUNDRY_ORCA_PROFILES to a directory containing the Foundry override "
                    f"files (e.g. Ender3_Klipper.json)."
                ) from exc

        machine = _resolve_or_foundry_fallback(
            printer.machine_name,
            DEFAULT_FOUNDRY_ORCA / "Ender3_Klipper.json",
            tmp / "machine.json",
            role="machine",
        )
        process = _resolve_or_foundry_fallback(
            printer.process_name,
            DEFAULT_FOUNDRY_ORCA / "Foundry_Process_0.20.json",
            tmp / "process.json",
            role="process",
        )
        filament = _resolve_or_foundry_fallback(
            printer.filament_name,
            DEFAULT_FOUNDRY_ORCA / "Silk_PLA.json",
            tmp / "filament.json",
            role="filament",
        )

        root = _orca_root()
        binary = root / "bin" / "orca-slicer"
        outdir = output.parent if output.suffix else output
        outdir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = _orca_lib_path(root) + ":" + env.get("LD_LIBRARY_PATH", "")
        # Orca: --slice 0 means all plates. Only pin a plate when magnet policy asks.
        plate = 0 if slice_plate is None else int(slice_plate)
        argv = [
            "xvfb-run", "-a", str(binary),
            *[str(m) for m in models],
            "--load-settings", f"{machine};{process}",
            "--load-filaments", str(filament),
        ]
        if abs(scale - 1.0) > 1e-6:
            argv.extend(["--scale", str(scale)])
        if repetitions > 1:
            argv.extend(["--repetitions", str(repetitions)])
        argv.extend([
            "--arrange", str(arrange),
            "--orient", str(orient),
            "--slice", str(plate),
            "--outputdir", str(outdir),
        ])
        return BackendCmd(
            argv=argv,
            env=env,
            flattened_machine=machine,
            flattened_process=process,
            flattened_filament=filament,
        )

    raise ValueError(f"unsupported backend {printer.backend!r}")


def run_backend(cmd: BackendCmd, *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    if not shutil.which("xvfb-run"):
        raise RuntimeError("xvfb-run not installed (required for headless slicing)")
    return subprocess.run(
        cmd.argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=cmd.env,
    )
