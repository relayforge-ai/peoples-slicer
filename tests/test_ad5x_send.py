"""Regression tests for the AD5X send() path — the two criticals that shipped untested:
single-color start (M23 selects, M6030 starts) and multicolor routing to /printGcode."""
import socket
import zipfile

from forge.adapters.ad5x import AD5XAdapter


class FakeSock:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, _t):
        pass

    def recv(self, _n):
        return b"ok\r\n"  # every ~command acknowledges

    def close(self):
        pass


def _patch_socket(monkeypatch, fake):
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: fake)


def test_single_color_send_selects_AND_starts(tmp_path, monkeypatch):
    fake = FakeSock()
    _patch_socket(monkeypatch, fake)
    gc = tmp_path / "cube.gcode"
    gc.write_bytes(b"G28\nG1 X0\n")

    AD5XAdapter("h", "s", "c").send(str(gc), start=True)

    sent = b"".join(fake.sent)
    assert b"M23 0:/user/cube.gcode" in sent          # select
    assert b'M6030 ":/user/cube.gcode"' in sent       # START — the bug: fired only if M23 failed


def _make_multicolor_3mf(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Metadata/plate_1.gcode", "; filament_colour = #FF0000;#00FF00\nG28\n")


def test_multicolor_send_routes_to_printGcode_with_ifs_map(tmp_path, monkeypatch):
    fake = FakeSock()
    _patch_socket(monkeypatch, fake)
    mc = tmp_path / "duo.gcode.3mf"
    _make_multicolor_3mf(str(mc))

    posted = []
    detail = {"status": "ready", "matlStationInfo": {"slotInfos": [
        {"slotId": 1, "materialColor": "#FE0000", "materialName": "PLA", "hasFilament": True},
        {"slotId": 2, "materialColor": "#00FE00", "materialName": "PLA", "hasFilament": True},
    ]}}
    a = AD5XAdapter(
        "h", "s", "c",
        detail_fetcher=lambda: detail,
        api_poster=lambda p, b: (posted.append((p, b)) or {"ok": True}),
    )
    a.send(str(mc), start=True)

    # a multicolor job must NOT take the mono socket-start path
    assert b"M6030" not in b"".join(fake.sent)
    # the keystone: /printGcode with useMatlStation + a 2-tool nearest-RGB material map
    assert posted, "send_multicolor never fired /printGcode — keystone unwired"
    path, body = posted[-1]
    assert path == "/printGcode"
    assert body["useMatlStation"] is True
    assert len(body["materialMappings"]) == 2
    m = {mm["toolId"]: mm["slotId"] for mm in body["materialMappings"]}
    assert m[0] == 1 and m[1] == 2  # red->slot1(#FE0000), green->slot2(#00FE00)


def test_empty_ifs_slot_never_wins_the_color_match():
    # an empty slot whose stale color is nearest must be skipped (hasFilament gate)
    slots = [
        {"slotId": 1, "materialColor": "#FF0000", "hasFilament": False},  # empty but exact red
        {"slotId": 2, "materialColor": "#CC0000", "hasFilament": True},   # loaded, close red
    ]
    maps = AD5XAdapter.build_mappings(["#FF0000"], slots)
    assert maps[0]["slotId"] == 2  # picks the LOADED slot, not the empty exact match
