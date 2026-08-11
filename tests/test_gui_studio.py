"""Local Studio GUI — brand, assets, health API, fail-closed bind."""
from __future__ import annotations

from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from importlib.resources import files
from io import BytesIO
import json
from threading import Thread
from types import SimpleNamespace

import pytest

from forge import BRAND, __version__
from forge.gui_server import (
    GUI_DIR,
    MAX_JSON_BYTES,
    MAX_UPLOAD_BYTES,
    RequestTooLarge,
    _api_send,
    _api_slice,
    _parse_multipart,
    _read_json,
    make_handler,
    serve,
)


@contextmanager
def running_studio():
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(None))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def request(port, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_brand_has_no_telchar_or_secrets():
    blob = json.dumps(BRAND) + BRAND["product"] + BRAND["tagline"]
    low = blob.lower()
    assert "telchar" not in low
    assert "relayforge.tools" not in low
    assert "people" in low
    assert BRAND["cli"] == "forge"


def test_gui_assets_exist():
    package = files("forge")
    for name in ("index.html", "styles.css", "app.js"):
        assert package.joinpath("gui", name).is_file()
    html = (GUI_DIR / "index.html").read_text(encoding="utf-8")
    assert "People's Slicer" in html
    assert "telchar" not in html.lower()
    assert "http://" not in html
    assert "https://" not in html


def test_printer_options_are_built_as_text_nodes():
    script = (GUI_DIR / "app.js").read_text(encoding="utf-8")
    assert 'document.createElement("option")' in script
    assert "sel.replaceChildren(...options)" in script
    assert '<option value="${p.key}">' not in script


def test_serve_rejects_non_localhost():
    with pytest.raises(ValueError, match="localhost"):
        serve(host="0.0.0.0", port=9, open_browser=False)


def test_http_serves_health_and_gui_with_security_headers():
    with running_studio() as port:
        status, headers, body = request(port, "GET", "/api/health")
        assert status == 200
        assert json.loads(body)["version"] == __version__
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

        status, _, body = request(port, "GET", "/")
        assert status == 200
        assert b"People's Slicer" in body


def test_http_rejects_cross_site_post_but_allows_local_origin():
    body = b"{}"
    base_headers = {"Content-Type": "application/json"}
    with running_studio() as port:
        status, _, response = request(
            port,
            "POST",
            "/api/send",
            body,
            {**base_headers, "Origin": "https://attacker.example"},
        )
        assert status == 403
        assert json.loads(response)["error"] == "cross-site requests are not allowed"

        status, _, response = request(
            port,
            "POST",
            "/api/send",
            body,
            {**base_headers, "Origin": f"http://127.0.0.1:{port}"},
        )
        assert status == 400
        assert json.loads(response)["error"] == "path required"


def test_request_body_limits_are_checked_before_reading():
    json_handler = SimpleNamespace(
        headers={"Content-Length": str(MAX_JSON_BYTES + 1)},
        rfile=BytesIO(),
    )
    with pytest.raises(RequestTooLarge, match="1 MiB"):
        _read_json(json_handler)

    upload_handler = SimpleNamespace(
        headers={
            "Content-Type": "multipart/form-data; boundary=test",
            "Content-Length": str(MAX_UPLOAD_BYTES + 1),
        },
        rfile=BytesIO(),
    )
    with pytest.raises(RequestTooLarge, match="256 MiB"):
        _parse_multipart(upload_handler)


def test_slice_api_parses_string_booleans(monkeypatch, tmp_path):
    model = tmp_path / "model.stl"
    model.write_text("solid x\nendsolid x\n")
    captured = {}

    def fake_slice_for(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            ok=True,
            printer="a1mini",
            backend="bambu",
            output=str(tmp_path / "out.gcode.3mf"),
            bounds=None,
            estimates={},
            scale=1.0,
            repetitions=1,
            detail="ok",
        )

    monkeypatch.setattr("forge.slice.slice_for", fake_slice_for)
    status, body, _ = _api_slice(
        {"printer": "a1mini", "dry_run": "false", "auto_refit": "false"},
        upload=model,
    )
    assert status == 200
    assert json.loads(body)["dry_run"] is False
    assert captured["dry_run"] is False
    assert captured["auto_refit"] is False


def test_send_api_does_not_treat_false_string_as_true(tmp_path):
    gcode = tmp_path / "model.gcode"
    gcode.write_text("; printer_model = Ender-3\n")
    status, body, _ = _api_send(
        {"path": str(gcode), "dry_run": "false", "bed_confirmed": "false"},
        None,
    )
    assert status == 403
    assert json.loads(body)["kind"] == "guardian"


def test_api_rejects_ambiguous_boolean(tmp_path):
    gcode = tmp_path / "model.gcode"
    gcode.write_text("; printer_model = Ender-3\n")
    status, body, _ = _api_send(
        {"path": str(gcode), "dry_run": "sometimes", "bed_confirmed": False},
        None,
    )
    assert status == 400
    assert json.loads(body)["error"] == "dry_run must be true or false"


def test_cli_lists_gui():
    from forge.cli import SUBCOMMANDS, build_parser

    assert "gui" in SUBCOMMANDS
    p = build_parser()
    args = p.parse_args(["gui", "--no-browser", "--port", "18765"])
    assert args.command == "gui"
    assert args.no_browser is True
