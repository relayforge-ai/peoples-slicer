from pathlib import Path

from forge import fixtures
from forge.review import parse_config_params, review_file, review_params

ROOT = Path(fixtures.FIXTURES_ROOT)


def test_parse_config_params_reads_semicolon_lines():
    meta = "; brim_width = 5\n; wall_loops = 2\n; enable_support = 0\nG1 X0"
    params = parse_config_params(meta)
    assert params["brim_width"] == "5"
    assert params["enable_support"] == "0"


def test_ender_golden_review_flags_thin_brim_if_zero():
    path = ROOT / "ender" / "golden.gcode"
    report = review_file(str(path))
    assert report["classified_printer"] == "ender"
    params = {f["param"]: f for f in report["findings"]}
    assert params["brim_width"]["severity"] == "ok"
    assert params["brim_width"]["value"] == 5.0


def test_review_params_suggests_low_brim_for_ender():
    findings = review_params({"brim_width": "0", "wall_loops": "2"}, "ender", "PLA")
    brim = next(f for f in findings if f.param == "brim_width")
    assert brim.severity == "suggest"


def test_flex_on_bambu_warns_wrong_route():
    findings = review_params({}, "bambu_a2l", "TPU")
    route = next(f for f in findings if f.param == "material_route")
    assert route.severity == "warn"
    assert "AD5X" in route.message