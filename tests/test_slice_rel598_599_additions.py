"""REL-598/599 additions — AMS map, routing ledger, multi-plate plan."""
from __future__ import annotations

from pathlib import Path

from forge.slice.ams_map import map_colors_to_ams
from forge.slice.multi_plate import inject_plate_change_into_machine, slice_batch
from forge.slice.routing_ledger import load_ledger, record_fit_failure


def test_ams_map_gs_colors():
    # Studio default trays: black=0 white=1 red=2 tan=3
    m = map_colors_to_ams(["tan", "black", "white"])
    assert m["use_ams"] is True
    assert m["ams_mapping"] == [3, 0, 1]
    assert m["ok"] is True


def test_ams_map_hex():
    m = map_colors_to_ams(["#AE835B", "#000000", "#FFFFFF"])
    assert m["ams_mapping"][0] == 3
    assert m["ok"] is True


def test_routing_ledger(tmp_path):
    ledger = tmp_path / "facts.json"
    fact = record_fit_failure(
        model="/tmp/big.3mf",
        printer="a1mini",
        message="too big",
        bounds={"dx": 200, "dy": 200, "dz": 50},
        sku="xxl-skeleton",
        path=ledger,
    )
    assert fact["kind"] == "does_not_fit"
    data = load_ledger(ledger)
    assert data["by_sku"]["xxl-skeleton"]["printer"] == "a1mini"


def test_inject_plate_change(tmp_path):
    machine = tmp_path / "machine.json"
    machine.write_text('{"name": "test", "type": "machine"}\n')
    out = inject_plate_change_into_machine(machine, "; eject\nG1 X0\n")
    import json
    d = json.loads(out.read_text())
    assert "plate_change_gcode" in d
    assert "eject" in d["plate_change_gcode"]


def test_slice_batch_dry_run(tmp_path):
    models = [str(tmp_path / f"m{i}.stl") for i in range(3)]
    for m in models:
        Path(m).write_text("solid x\nendsolid x\n")
    r = slice_batch(models, dry_run=True)
    assert r.printer == "a1mini"
    assert len(r.plates) == 3
    assert all(p["status"] == "planned" for p in r.plates)
