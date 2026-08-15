from forge.guardian import Guardian


def test_vetoes_when_bed_not_confirmed():
    g = Guardian()
    approved, reason = g.approve({"path": "/a.gcode", "bed_confirmed_clear": False})
    assert approved is False
    assert "bed" in reason


def test_allows_when_bed_confirmed():
    g = Guardian()
    approved, _ = g.approve({"path": "/a.gcode", "bed_confirmed_clear": True, "colors": 1})
    assert approved is True


def test_vetoes_flex_on_wrong_printer():
    g = Guardian()
    approved, reason = g.approve({
        "path": "/a.gcode",
        "material": "TPU",
        "printer": "bambu",
        "colors": 1,
        "bed_confirmed_clear": True,
    })
    assert approved is False
    assert "AD5X" in reason


def test_pluggable_veto_hook():
    def hook(job):
        return False, "amos says no"

    g = Guardian(veto_hook=hook)
    approved, reason = g.approve({"path": "/a.gcode", "colors": 1, "bed_confirmed_clear": True})
    assert approved is False
    assert reason == "amos says no"


def test_vetoes_when_bed_unspecified():
    # fail-CLOSED regression: a job that never confirms the bed must NOT proceed
    g = Guardian()
    approved, reason = g.approve({"path": "/a.gcode", "colors": 1})
    assert approved is False
    assert "bed" in reason

def test_flex_vetoed_on_ender():
    g = Guardian()
    ok, reason = g.approve({"path": "/x.gcode", "bed_confirmed_clear": True, "material": "TPU", "printer": "ender"})
    assert not ok
    assert "AD5X" in reason


def test_multicolor_without_prime_tower_is_vetoed_for_every_printer():
    g = Guardian()
    for printer in ("ad5x", "bambu", "kobra3max", "ender"):
        ok, reason = g.approve({
            "path": "/x.gcode",
            "bed_confirmed_clear": True,
            "material": "PLA",
            "printer": printer,
            "colors": 2,
            "prime_tower_enabled": False,
        })
        assert not ok, printer
        assert "prime_tower" in reason


def test_multicolor_with_verified_prime_tower_passes_tower_gate():
    g = Guardian()
    ok, reason = g.approve({
        "path": "/x.gcode",
        "bed_confirmed_clear": True,
        "material": "PLA",
        "printer": "ad5x",
        "colors": 4,
        "prime_tower_enabled": True,
    })
    assert ok
    assert reason == "ok"
