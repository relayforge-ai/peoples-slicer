"""fill-20260901-a1mini-flexypup — Kobra-origin 3mf must not leak onto A1 mini.

Verified on Dawes: --load-settings rewrote printer_model but left
enable_prime_tower=0 and wipe_tower_y=220. REL-602 validation must stay
strict; retarget/flatten must make the artifact pass it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge.slice import backends
from forge.slice.api import SliceError, slice_for
from forge.slice.artifact import ArtifactError, assert_sliced_artifact
from forge.slice.backends import build_backend_cmd
from forge.slice.magnet_plates import select_magnet_plate
from forge.slice.printers import get_printer
from forge.slice.profile_resolve import ProfileIndex
from forge.slice.retarget import (
    color_count_from_path,
    read_embedded_project_settings,
    sanitize_project_3mf,
    stamp_target_overrides,
    wipe_tower_inside_bed,
)

from tests.slice_helpers import (
    write_kobra_flexypup_3mf,
    write_sliced_3mf,
    write_studio_profile_tree,
)


KOBRA_COLOURS = "#80FF80;#FFFFFF;#0000FF;#6F5034;#FFFF00"
A1_AREA = ["0x0", "180x0", "180x180", "0x180"]


def test_kobra_source_is_the_verified_leak(tmp_path):
    src = write_kobra_flexypup_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    raw = read_embedded_project_settings(src)
    assert raw is not None
    assert raw["enable_prime_tower"] in (0, "0")
    assert float(raw["wipe_tower_y"]) == 220
    assert raw["filament_colour"] == KOBRA_COLOURS
    assert color_count_from_path(src) == 5
    assert select_magnet_plate(src).slice_plate == 2


def test_retarget_forces_prime_tower_and_clamps_wipe_to_180(tmp_path):
    src = write_kobra_flexypup_3mf(tmp_path / "kobra.3mf")
    dest = tmp_path / "retargeted.3mf"
    spec = get_printer("a1mini")
    machine = {
        "name": spec.machine_name,
        "printer_model": "Bambu Lab A1 mini",
        "printable_area": A1_AREA,
        "printable_height": "180",
    }
    process = {"name": spec.process_name, "enable_prime_tower": "1"}
    sanitize_project_3mf(src, dest, spec, colors=5, machine=machine, process=process)
    out = read_embedded_project_settings(dest)
    assert out is not None
    assert out["enable_prime_tower"] == "1"
    assert out["printer_model"] == "Bambu Lab A1 mini"
    assert out["printable_area"] == A1_AREA
    assert wipe_tower_inside_bed(out, 180.0)
    assert float(out["wipe_tower_y"]) <= 180 - 35
    assert out["filament_colour"] == KOBRA_COLOURS
    # source file must stay dirty — we copy, we do not mutate the maker 3mf
    leaked = read_embedded_project_settings(src)
    assert leaked is not None
    assert leaked["enable_prime_tower"] in (0, "0")
    assert float(leaked["wipe_tower_y"]) == 220


def test_rel602_validation_still_rejects_tower_off_multicolor(tmp_path):
    leaked = write_sliced_3mf(
        tmp_path / "leaked.gcode.3mf",
        printer_model="Bambu Lab A1 mini",
        printable_area=A1_AREA,
        extra_settings={
            "enable_prime_tower": "0",
            "wipe_tower_x": "220",
            "wipe_tower_y": "220",
            "filament_colour": KOBRA_COLOURS,
        },
        gcode_extra=(
            f"; filament_colour = {KOBRA_COLOURS}\n"
            "; enable_prime_tower = 0\n"
        ),
    )
    with pytest.raises(ArtifactError, match="enable_prime_tower = 1"):
        assert_sliced_artifact(leaked, "a1mini")
    with pytest.raises(ArtifactError, match="REL-602 output validation failed"):
        assert_sliced_artifact(leaked, "a1mini")


def test_rel602_validation_rejects_wipe_tower_off_bed(tmp_path):
    bad = write_sliced_3mf(
        tmp_path / "wipe220.gcode.3mf",
        printer_model="Bambu Lab A1 mini",
        printable_area=A1_AREA,
        extra_settings={
            "enable_prime_tower": "1",
            "wipe_tower_x": "135",
            "wipe_tower_y": "220",
            "filament_colour": KOBRA_COLOURS,
        },
    )
    with pytest.raises(ArtifactError, match="wipe_tower"):
        assert_sliced_artifact(bad, "a1mini")


def test_rel602_validation_accepts_retargeted_five_color_a1mini(tmp_path):
    good = write_sliced_3mf(
        tmp_path / "ok.gcode.3mf",
        printer_model="Bambu Lab A1 mini",
        printable_area=A1_AREA,
        extra_settings={
            "enable_prime_tower": "1",
            "wipe_tower_x": "137",
            "wipe_tower_y": "137",
            "prime_tower_width": "35",
            "filament_colour": KOBRA_COLOURS,
        },
    )
    cfg = assert_sliced_artifact(good, "a1mini")
    assert cfg["enable_prime_tower"] == "1"
    assert wipe_tower_inside_bed(cfg, 180.0)


def test_five_color_kobra_retargeted_to_a1mini_stamps_process(tmp_path, monkeypatch):
    """THE test for fill-20260901-a1mini-flexypup.

    A 5-color Kobra-origin 3mf retargeted to A1 mini must feed the slicer
    enable_prime_tower=1 and a wipe tower inside 180×180 — not the source 0/220.
    """
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    src = write_kobra_flexypup_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    spec = get_printer("a1mini")
    cmd = build_backend_cmd(
        spec, src, tmp_path / "out.gcode.3mf", profile_dir=tmp_path / "flat"
    )
    process = json.loads(Path(cmd.flattened_process).read_text())
    assert process["enable_prime_tower"] == "1"
    assert wipe_tower_inside_bed(process, 180.0)
    assert cmd.color_count == 5

    models = cmd.argv[cmd.argv.index("--export-3mf") + 2 :]
    assert len(models) == 1
    fed = Path(models[0])
    assert fed != src
    fed_settings = read_embedded_project_settings(fed)
    assert fed_settings is not None
    assert fed_settings["enable_prime_tower"] == "1"
    assert fed_settings["printable_area"] == A1_AREA
    assert wipe_tower_inside_bed(fed_settings, 180.0)
    assert float(fed_settings["wipe_tower_y"]) != 220

    result = slice_for(src, "a1mini", dry_run=True)
    assert result.slice_plate == 2
    assert result.estimates["enable_prime_tower"] == "1"
    assert result.estimates["colors"] == 5
    assert wipe_tower_inside_bed(result.estimates, 180.0)


def test_stamp_does_not_force_tower_on_single_color():
    spec = get_printer("a1mini")
    out = stamp_target_overrides(
        {"enable_prime_tower": "0", "wipe_tower_y": "220"},
        spec,
        colors=1,
        machine={"printable_area": A1_AREA, "printer_model": "Bambu Lab A1 mini"},
    )
    assert out["enable_prime_tower"] == "0"
    assert wipe_tower_inside_bed(out, 180.0)


def test_slice_for_raises_rel602_wording_on_bad_artifact(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    src = write_kobra_flexypup_3mf(tmp_path / "kobra.3mf")
    out = tmp_path / "out.gcode.3mf"

    def _fake_run(cmd, *, timeout=900):
        # Simulate the Dawes leak: slicer kept source tower=0 / y=220.
        write_sliced_3mf(
            out,
            printer_model="Bambu Lab A1 mini",
            printable_area=A1_AREA,
            extra_settings={
                "enable_prime_tower": "0",
                "wipe_tower_y": "220",
                "filament_colour": KOBRA_COLOURS,
            },
        )
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("forge.slice.api.run_backend", _fake_run)
    with pytest.raises(SliceError, match="REL-602 output validation failed"):
        slice_for(src, "a1mini", output=out, skip_fit_check=True)
