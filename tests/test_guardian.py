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
    })
    assert approved is False
    assert "AD5X" in reason


def test_pluggable_veto_hook():
    def hook(job):
        return False, "amos says no"

    g = Guardian(veto_hook=hook)
    approved, reason = g.approve({"path": "/a.gcode", "colors": 1})
    assert approved is False
    assert reason == "amos says no"