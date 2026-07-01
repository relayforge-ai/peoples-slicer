import json

import pytest

from forge import fixtures


def test_missing_fixture_points_at_the_runbook():
    with pytest.raises(fixtures.FixtureNotFound) as exc:
        fixtures.load("ad5x", "does_not_exist")
    assert "capture" in str(exc.value).lower()


def test_round_trip_json_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "FIXTURES_ROOT", tmp_path)
    (tmp_path / "ad5x").mkdir()
    payload = {"useMatlStation": True, "materialMappings": [{"toolId": 0, "slotId": 1}]}
    (tmp_path / "ad5x" / "print_gcode_request.json").write_text(json.dumps(payload))
    assert fixtures.load("ad5x", "print_gcode_request") == payload
    assert "print_gcode_request" in fixtures.available("ad5x")


def test_load_text_reads_gcode(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "FIXTURES_ROOT", tmp_path)
    (tmp_path / "bambu_a2l").mkdir()
    (tmp_path / "bambu_a2l" / "golden.gcode").write_text("; header\nG28\n")
    assert "G28" in fixtures.load_text("bambu_a2l", "golden.gcode")
