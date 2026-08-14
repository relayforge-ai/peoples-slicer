"""Bambu adapter — AMS color mapping, upload verify, and multicolor send wiring."""
import zipfile

from forge.adapters.bambu import BambuAdapter
from forge import fixtures


def test_mqtt_color_to_hex_strips_alpha():
    assert BambuAdapter._mqtt_color_to_hex("D3B7A7FF") == "#D3B7A7"


def test_parse_ams_trays_from_fixture():
    trays = BambuAdapter.parse_ams_trays(fixtures.load("bambu_a2l", "ams_slot_state"))
    assert [t["slot"] for t in trays] == [0, 1, 2, 3]
    assert trays[3]["color"] == "#D3B7A7"


def test_build_ams_mapping_matches_nearest_tray():
    trays = BambuAdapter.parse_ams_trays(fixtures.load("bambu_a2l", "ams_slot_state"))
    # German Shepherd hatchling colors from the 2026-06-29 batch: tan, black, white.
    mapping = BambuAdapter.build_ams_mapping(["#AE835B", "#000000", "#FFFFFF"], trays)
    assert mapping == [3, 0, 1]


def test_empty_tray_never_wins_color_match():
    trays = BambuAdapter.parse_ams_trays(
        {
            "ams": [
                {
                    "id": "0",
                    "tray": [
                        {"id": "0"},
                        {"id": "1", "tray_color": "CC0000FF", "tray_type": "PLA"},
                    ],
                }
            ]
        }
    )
    assert BambuAdapter.build_ams_mapping(["#FF0000"], trays) == [1]


def test_upload_verifies_remote_size(tmp_path, monkeypatch):
    class FakeFTP:
        def __init__(self):
            self.stored = b""
            self.closed = False
            self.quit_called = False

        def connect(self, *_a, **_k):
            pass

        def login(self, *_a, **_k):
            pass

        def prot_p(self):
            pass

        def storbinary(self, _cmd, fh):
            self.stored = fh.read()

        def size(self, _path):
            return len(self.stored)

        def quit(self):
            self.quit_called = True

        def close(self):
            self.closed = True

    fake = FakeFTP()
    monkeypatch.setattr(
        "forge.adapters.bambu.ImplicitFTP_TLS",
        lambda *a, **k: fake,
    )
    local = tmp_path / "job.gcode.3mf"
    local.write_bytes(b"slice-data")
    remote = BambuAdapter("h", "c", "s")._upload(str(local), local.name)
    assert remote == f"/{local.name}"
    assert fake.closed is True
    assert fake.quit_called is False


def test_upload_rejects_size_mismatch(tmp_path, monkeypatch):
    class BadFTP:
        def connect(self, *_a, **_k):
            pass

        def login(self, *_a, **_k):
            pass

        def prot_p(self):
            pass

        def storbinary(self, _cmd, _fh):
            pass

        def size(self, _path):
            return 1

        def quit(self):
            pass

    monkeypatch.setattr("forge.adapters.bambu.ImplicitFTP_TLS", lambda *a, **k: BadFTP())
    local = tmp_path / "job.gcode.3mf"
    local.write_bytes(b"0123456789")
    try:
        BambuAdapter("h", "c", "s", upload_retries=1)._upload(str(local), local.name)
        assert False, "expected size mismatch"
    except RuntimeError as exc:
        msg = str(exc.__cause__ or exc)
        assert "size mismatch" in msg


def test_upload_closes_connection_before_retrying(tmp_path, monkeypatch):
    # A failed attempt must not leave its FTPS connection open — Bambu's control
    # channel allows only one session, so a leaked connection could block the retry.
    made = []

    class FlakyThenGoodFTP:
        def __init__(self):
            self.closed = False
            made.append(self)

        def connect(self, *_a, **_k):
            pass

        def login(self, *_a, **_k):
            pass

        def prot_p(self):
            pass

        def storbinary(self, _cmd, fh):
            if len(made) == 1:
                raise ConnectionResetError("connection reset mid-transfer")
            self.stored = fh.read()

        def size(self, _path):
            return len(self.stored)

        def quit(self):
            pass

        def close(self):
            self.closed = True

    monkeypatch.setattr("forge.adapters.bambu.ImplicitFTP_TLS", lambda *a, **k: FlakyThenGoodFTP())
    local = tmp_path / "job.gcode.3mf"
    local.write_bytes(b"slice-data")

    remote = BambuAdapter("h", "c", "s", upload_retries=2)._upload(str(local), local.name)

    assert remote == f"/{local.name}"
    assert len(made) == 2
    assert made[0].closed is True  # the failed first attempt was cleaned up


def _make_multicolor_3mf(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "Metadata/plate_1.gcode",
            "; filament_colour = #AE835B;#000000;#FFFFFF\nG28\n",
        )


def _make_single_color_3mf(path, color="#00FF00"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "Metadata/plate_1.gcode",
            f"; filament_colour = {color}\nG28\n",
        )


def _make_single_used_color_with_extra_palette_3mf(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "Metadata/plate_1.gcode",
            "; filament_colour = #00FF00;#D4B1DD;#4D3C22;#FFFFFF\nG28\n",
        )
        zf.writestr(
            "Metadata/slice_info.config",
            '<?xml version="1.0"?><config><plate>'
            '<filament id="1" color="#00FF00" used_for_object="true"/>'
            '</plate></config>',
        )


def test_multicolor_send_auto_maps_ams(tmp_path):
    mc = tmp_path / "trio.gcode.3mf"
    _make_multicolor_3mf(str(mc))
    trays = fixtures.load("bambu_a2l", "ams_slot_state")
    published = []

    a = BambuAdapter(
        "h",
        "access",
        "serial",
        ftps_uploader=lambda _l, n: f"/{n}",
        state_fetcher=lambda: {"ams": trays},
        mqtt_publisher=lambda payload, _wait: (published.append(payload) or {"ok": True}),
    )
    a.send(str(mc), start=True)
    assert published
    assert published[0]["print"]["ams_mapping"] == [3, 0, 1]


def test_single_color_send_uses_nearest_loaded_ams_tray(tmp_path):
    job = tmp_path / "single.gcode.3mf"
    _make_single_color_3mf(str(job), "#00FF00")
    trays = {
        "ams": [{
            "id": "0",
            "tray": [
                {"id": "0", "tray_color": "0086D6FF", "tray_type": "PLA"},
                {"id": "1", "tray_color": "000000FF", "tray_type": "PLA"},
                {"id": "2", "tray_color": "E9AFCFFF", "tray_type": "PLA"},
                {"id": "3", "tray_color": "FFFFFFFF", "tray_type": "PLA"},
            ],
        }]
    }
    published = []
    adapter = BambuAdapter(
        "h",
        "access",
        "serial",
        ftps_uploader=lambda _local, name: f"/{name}",
        state_fetcher=lambda: {"ams": trays},
        mqtt_publisher=lambda payload, _wait: (published.append(payload) or {"ok": True}),
    )

    adapter.send(str(job), start=True)

    assert published[0]["print"]["use_ams"] is True
    assert published[0]["print"]["ams_mapping"] == [0]


def test_tool_colors_ignores_unused_3mf_palette_entries(tmp_path):
    job = tmp_path / "single-with-palette.gcode.3mf"
    _make_single_used_color_with_extra_palette_3mf(str(job))

    assert BambuAdapter.tool_colors(str(job)) == ["#00FF00"]


def test_single_color_send_allows_external_spool_when_no_ams(tmp_path):
    job = tmp_path / "single.gcode.3mf"
    _make_single_color_3mf(str(job))
    published = []
    adapter = BambuAdapter(
        "h",
        "access",
        "serial",
        ftps_uploader=lambda _local, name: f"/{name}",
        state_fetcher=lambda: {},
        mqtt_publisher=lambda payload, _wait: (published.append(payload) or {"ok": True}),
    )

    adapter.send(str(job), start=True)

    assert published[0]["print"]["use_ams"] is False
    assert published[0]["print"]["ams_mapping"] == [0]


def test_single_color_send_allows_external_spool_when_ams_read_fails(tmp_path):
    job = tmp_path / "single.gcode.3mf"
    _make_single_color_3mf(str(job))
    published = []

    def failed_state_read():
        raise TimeoutError("AMS state unavailable")

    adapter = BambuAdapter(
        "h",
        "access",
        "serial",
        ftps_uploader=lambda _local, name: f"/{name}",
        state_fetcher=failed_state_read,
        mqtt_publisher=lambda payload, _wait: (published.append(payload) or {"ok": True}),
    )

    adapter.send(str(job), start=True)

    assert published[0]["print"]["use_ams"] is False
    assert published[0]["print"]["ams_mapping"] == [0]


def test_tool_colors_reads_from_3mf(tmp_path):
    mc = tmp_path / "duo.gcode.3mf"
    _make_multicolor_3mf(str(mc))
    assert BambuAdapter.tool_colors(str(mc)) == ["#AE835B", "#000000", "#FFFFFF"]
