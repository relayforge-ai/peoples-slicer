"""Golden g-code fixtures must classify to the right printer without a live LAN."""
from pathlib import Path

from forge import fixtures
from forge.reader import classify_file

ROOT = Path(fixtures.FIXTURES_ROOT)


def test_ender_golden_classifies_via_settings_id():
    path = ROOT / "ender" / "golden.gcode"
    info = classify_file(str(path))
    assert info.printer == "ender"
    assert info.material == "PLA"


def test_bambu_a2l_golden_classifies():
    path = ROOT / "bambu_a2l" / "golden.gcode"
    info = classify_file(str(path))
    assert info.printer == "bambu_a2l"
    # German Shepherd hatchling batch (gs4.gcode.3mf): tan + black + white.
    assert info.colors == 3


def test_ad5x_multicolor_golden_classifies():
    path = ROOT / "ad5x" / "golden_multicolor.gcode.3mf"
    info = classify_file(str(path))
    assert info.printer == "ad5x"
    assert info.colors == 2
    assert info.material == "TPU"