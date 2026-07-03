from forge.dispatcher import Dispatcher
from forge.jobqueue import JobQueue


class FakeAdapter:
    """Stands in for a real printer adapter — no network."""

    def __init__(self, status="idle"):
        self._status = status
        self.sent = []

    def status(self):
        return self._status

    def send(self, gcode_path, start):
        self.sent.append((gcode_path, start))
        return "job-token"


def _write_gcode(tmp_path, model="Flashforge AD5X", name="job.gcode"):
    body = "".join(f"G1 X{i % 100} E{i * 0.01:.2f}\n" for i in range(100))
    content = (
        "; HEADER_BLOCK_START\n; filament: 1\n; HEADER_BLOCK_END\n"
        + body
        + "; CONFIG_BLOCK_START\n"
        "; filament_type = TPU\n; total filament used [g] = 33.53\n"
        f"; printer_model = {model}\n; CONFIG_BLOCK_END\n"
    )
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def _dispatcher(tmp_path, adapter):
    q = JobQueue(str(tmp_path / "state.json"))
    return Dispatcher(adapters={"ad5x": adapter}, queue=q), q


def test_idle_printer_sends_immediately(tmp_path):
    ad5x = FakeAdapter("idle")
    d, q = _dispatcher(tmp_path, ad5x)
    res = d.submit(_write_gcode(tmp_path))
    assert res["state"] == "printing"
    assert res["printer"] == "ad5x"
    assert len(ad5x.sent) == 1
    assert q.active("ad5x")["id"] == res["job_id"]


def test_busy_printer_queues(tmp_path):
    ad5x = FakeAdapter("printing")
    d, q = _dispatcher(tmp_path, ad5x)
    res = d.submit(_write_gcode(tmp_path))
    assert res["state"] == "queued"
    assert ad5x.sent == []
    assert [j["id"] for j in q.pending("ad5x")] == [res["job_id"]]


def test_unknown_printer_is_quarantined(tmp_path):
    ad5x = FakeAdapter("idle")
    d, _ = _dispatcher(tmp_path, ad5x)
    res = d.submit(_write_gcode(tmp_path, model="Prusa MK4"))
    assert res["state"] == "quarantined"
    assert ad5x.sent == []


def test_duplicate_submit_is_deduped(tmp_path):
    ad5x = FakeAdapter("idle")
    d, _ = _dispatcher(tmp_path, ad5x)
    g = _write_gcode(tmp_path)
    d.submit(g)
    res2 = d.submit(g)  # same content hash, already active
    assert res2["state"] == "duplicate"
    assert len(ad5x.sent) == 1


def test_events_are_recorded(tmp_path):
    ad5x = FakeAdapter("idle")
    d, _ = _dispatcher(tmp_path, ad5x)
    d.submit(_write_gcode(tmp_path))
    assert d.events[-1]["state"] == "printing"


def test_drain_sends_queued_job_when_printer_frees(tmp_path):
    ad5x = FakeAdapter("printing")
    d, q = _dispatcher(tmp_path, ad5x)
    res = d.submit(_write_gcode(tmp_path))  # busy -> queued
    assert res["state"] == "queued"
    ad5x._status = "idle"                    # printer frees
    drained = d.drain()
    assert len(ad5x.sent) == 1
    assert q.active("ad5x")["id"] == res["job_id"]
    assert drained[0]["state"] == "printing"


def test_drain_noop_when_printer_still_busy(tmp_path):
    ad5x = FakeAdapter("printing")
    d, _ = _dispatcher(tmp_path, ad5x)
    d.submit(_write_gcode(tmp_path))
    assert d.drain() == []
    assert ad5x.sent == []


def test_drain_does_not_start_second_job_while_active(tmp_path):
    ad5x = FakeAdapter("idle")
    d, q = _dispatcher(tmp_path, ad5x)
    d.submit(_write_gcode(tmp_path, name="a.gcode"))   # -> printing (active)
    ad5x._status = "printing"
    d.submit(_write_gcode(tmp_path, name="b.gcode", model="Flashforge AD5X B"))   # active exists -> queued
    sent_before = len(ad5x.sent)
    assert d.drain() == []                              # don't start b over a
    assert len(ad5x.sent) == sent_before


def test_drain_completes_idle_active_before_next(tmp_path):
    ad5x = FakeAdapter("idle")
    d, q = _dispatcher(tmp_path, ad5x)
    res1 = d.submit(_write_gcode(tmp_path, name="a.gcode"))
    assert res1["state"] == "printing"
    ad5x._status = "printing"
    d.submit(_write_gcode(tmp_path, name="b.gcode", model="Flashforge AD5X B"))
    ad5x._status = "idle"
    drained = d.drain()
    assert len(drained) == 1
    assert drained[0]["state"] == "printing"
    assert q.active("ad5x")["name"] == "b.gcode"


def test_drain_vetoes_without_bed_confirmed(tmp_path):
    from forge.guardian import Guardian

    ad5x = FakeAdapter("idle")
    q = JobQueue(str(tmp_path / "state.json"))
    d = Dispatcher(adapters={"ad5x": ad5x}, queue=q, guardian=Guardian())
    gpath = _write_gcode(tmp_path)
    q.enqueue("ad5x", {
        "id": "manual", "name": "job.gcode", "printer": "ad5x", "path": gpath,
        "material": "PLA", "colors": 1,
    })
    drained = d.drain()
    assert drained[0]["state"] == "vetoed"
    assert ad5x.sent == []
