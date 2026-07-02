from forge.adapters.klipper import KlipperAdapter
from forge import fixtures


def test_status_idle_from_fixture():
    status = fixtures.load("ender", "moonraker_status_idle")

    adapter = KlipperAdapter("http://pi.local:7125", status_fetcher=lambda: status)
    assert adapter.status() == "idle"


def test_status_printing():
    data = {
        "result": {
            "status": {
                "print_stats": {"state": "printing"},
                "webhooks": {"state": "ready"},
            }
        }
    }
    adapter = KlipperAdapter("http://pi.local:7125", status_fetcher=lambda: data)
    assert adapter.status() == "printing"


def test_firmware_restart_on_mcu_drop(tmp_path):
    gcode = tmp_path / "test.gcode"
    gcode.write_text("; test\n")
    calls: list[str] = []
    upload_attempts = 0

    def poster(method, path, data=None, headers=None):
        calls.append(f"{method} {path}")
        nonlocal upload_attempts
        if "upload" in path:
            upload_attempts += 1
            if upload_attempts == 1:
                raise RuntimeError('{"error": "Lost communication with MCU"}')
            return {}
        if "firmware_restart" in path:
            return {}
        if "print/start" in path:
            return {}
        return {}

    adapter = KlipperAdapter(
        "http://pi.local:7125",
        restart_wait_s=0,
        http_poster=poster,
        status_fetcher=lambda: fixtures.load("ender", "moonraker_status_idle"),
    )
    adapter.send(str(gcode), start=True)
    assert any("firmware_restart" in c for c in calls)