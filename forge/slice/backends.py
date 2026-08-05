"""Slicer backends: BambuStudio (a1mini, a2l) and OrcaSlicer (ad5x, ender)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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


def build_backend_cmd(
    printer: PrinterSpec,
    model: Path,
    output: Path,
    *,
    profile_dir: Path | None = None,
    scale: float = 1.0,
    repetitions: int = 1,
    arrange: int = 1,
    orient: int = 1,
) -> BackendCmd:
    """Build the headless CLI for this printer (does not execute)."""
    model = Path(model)
    output = Path(output)
    tmp = Path(profile_dir or tempfile.mkdtemp(prefix=f"mslice-{printer.key}-"))
    tmp.mkdir(parents=True, exist_ok=True)
    scale = float(scale) if scale and scale > 0 else 1.0
    repetitions = max(1, int(repetitions or 1))
    arrange = 0 if arrange == 0 else 1
    orient = 0 if orient == 0 else 1

    if printer.backend == "bambu":
        idx = bambu_index()
        machine = write_flattened(idx, printer.machine_name, tmp / "machine.json")
        process = write_flattened(idx, printer.process_name, tmp / "process.json")
        filament = write_flattened(idx, printer.filament_name, tmp / "filament.json")
        bs = _bambu_bin()
        # BambuStudio: plate 1, export gcode.3mf. load-settings = machine;process
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
            "--slice", "1",
            "--export-3mf", str(output),
            str(model),
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

        def _resolve_or_foundry_fallback(name: str, fallback: Path, dest: Path) -> Path:
            # Ender Foundry profiles live outside the AppImage tree and already inherit
            # stock Creality names; flatten when possible, else pass through the Foundry
            # leaf file — but only if that fallback actually exists. REL-631: silently
            # handing back a nonexistent fallback path recreates the same fail-open the
            # missing-vendor-profile case has: `cmd.flattened_machine` gets set to a Path
            # that was never validated, and downstream code only checks it when the path
            # happens to exist (`if cmd.flattened_machine and cmd.flattened_machine.exists()`)
            # — a nonexistent fallback would skip that check entirely instead of failing.
            try:
                return write_flattened(idx, name, dest)
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
            printer.machine_name, DEFAULT_FOUNDRY_ORCA / "Ender3_Klipper.json", tmp / "machine.json"
        )
        process = _resolve_or_foundry_fallback(
            printer.process_name, DEFAULT_FOUNDRY_ORCA / "Foundry_Process_0.20.json", tmp / "process.json"
        )
        filament = _resolve_or_foundry_fallback(
            printer.filament_name, DEFAULT_FOUNDRY_ORCA / "Silk_PLA.json", tmp / "filament.json"
        )

        root = _orca_root()
        binary = root / "bin" / "orca-slicer"
        outdir = output.parent if output.suffix else output
        outdir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = _orca_lib_path(root) + ":" + env.get("LD_LIBRARY_PATH", "")
        argv = [
            "xvfb-run", "-a", str(binary),
            str(model),
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
            "--slice", "0",
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
