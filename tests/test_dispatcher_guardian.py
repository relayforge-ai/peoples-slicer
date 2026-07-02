from forge.dispatcher import Dispatcher
from forge.guardian import Guardian
from forge.jobqueue import JobQueue


class FakeAdapter:
    def __init__(self, state="idle"):
        self.state = state
        self.sent = []

    def status(self):
        return self.state

    def send(self, path, start=True):
        self.sent.append(path)
        return "ok"


def test_submit_vetoed_by_guardian(tmp_path, monkeypatch):
    gcode = tmp_path / "job.gcode"
    gcode.write_text(
        "; printer_model = Bambu Lab A2L\n"
        "; filament_type = PLA\n"
        "; estimated printing time (normal mode) = 1h 2m 3s\n"
        "; total filament used [g] = 12.3\n"
    )

    monkeypatch.setattr(
        "forge.dispatcher.classify_file",
        lambda _p: type("I", (), {
            "printer": "bambu", "material": "PLA", "colors": 1,
            "est_seconds": 60, "est_grams": 1.0,
        })(),
    )

    adapter = FakeAdapter()
    dispatcher = Dispatcher(
        adapters={"bambu": adapter},
        queue=JobQueue(str(tmp_path / "q.json")),
        guardian=Guardian(),
    )
    result = dispatcher.submit(str(gcode), bed_confirmed_clear=False)
    assert result["state"] == "vetoed"
    assert adapter.sent == []