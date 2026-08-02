"""REL-600 / REL-601 — forge.slice policy + CLI surface."""
from __future__ import annotations

from pathlib import Path

import pytest

from forge import cli
from forge.slice import PRINTERS, get_printer, plan_plate, refit_scale
from forge.slice.plate_cycler import MAX_PLATES, plan_batches
from forge.slice.plate_swap import PlateSwapNotConfigured, plate_swap_end_gcode


def test_printer_routing_table():
    assert set(PRINTERS) == {"a1mini", "a2l", "ad5x", "ender"}
    assert get_printer("a1mini").bed_xy_mm == 180
    assert get_printer("a1mini").backend == "bambu"
    assert get_printer("ad5x").backend == "orca"


def test_mmmini_is_not_a_printer():
    with pytest.raises(KeyError):
        get_printer("MMMini")


def test_plate_change_not_invented():
    with pytest.raises(PlateSwapNotConfigured):
        plate_swap_end_gcode()


def test_plate_batches_cap():
    batches = plan_batches([f"/tmp/m{i}.3mf" for i in range(9)])
    assert all(len(b.models) <= MAX_PLATES for b in batches)
    assert len(batches) == 3


def test_refit_and_policy_on_ascii_stl(tmp_path):
    stl = tmp_path / "cube.stl"
    stl.write_text(
        "solid c\n"
        " facet normal 0 0 1\n  outer loop\n"
        "   vertex 0 0 0\n   vertex 20 0 0\n   vertex 20 20 0\n"
        "  endloop\n endfacet\n"
        " facet normal 0 0 1\n  outer loop\n"
        "   vertex 0 0 0\n   vertex 20 20 0\n   vertex 0 20 0\n"
        "  endloop\n endfacet\n"
        "endsolid c\n"
    )
    plan = refit_scale(stl, "a1mini")
    assert plan.fits_without_scale is True
    pol = plan_plate(stl, "a1mini", goal="max_parts")
    assert pol.repetitions >= 1
    assert pol.scale == 1.0


def test_cli_lists_slice_commands(capsys):
    rc = cli.main(["--help"])
    out = capsys.readouterr().out
    assert rc == 0
    for sub in ("slice", "slice-send", "harvest"):
        assert sub in out


def test_cli_slice_plan_only(tmp_path, capsys):
    stl = tmp_path / "p.stl"
    stl.write_text(
        "solid c\n facet normal 0 0 1\n  outer loop\n"
        "   vertex 0 0 0\n   vertex 10 0 0\n   vertex 10 10 0\n"
        "  endloop\n endfacet\n"
        " facet normal 0 0 1\n  outer loop\n"
        "   vertex 0 0 0\n   vertex 10 10 0\n   vertex 0 10 0\n"
        "  endloop\n endfacet\nendsolid c\n"
    )
    rc = cli.main(["slice", str(stl), "--printer", "a1mini", "--plan-only", "--goal", "single"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "policy" in out
    assert "refit" in out
