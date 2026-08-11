"""Local-only Studio UI for The People's Slicer.

Binds 127.0.0.1. Serves the static GUI and thin JSON APIs that call the same
slice / review / send code paths as the CLI. No cloud, no secrets in the tree.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import tempfile
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import BRAND, __version__

GUI_DIR = Path(__file__).resolve().parent.parent / "gui"
UPLOAD_ROOT = Path(tempfile.gettempdir()) / "peoples-slicer-studio"
_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _json_bytes(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, indent=2, default=str).encode("utf-8") + b"\n"
    return code, body, "application/json; charset=utf-8"


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    n = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(n) if n else b"{}"
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid json: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("json body must be an object")
    return data


def _parse_multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, bytes]]:
    """Minimal multipart/form-data parser (file + text fields)."""
    ctype = handler.headers.get("Content-Type") or ""
    if "multipart/form-data" not in ctype:
        raise ValueError("expected multipart/form-data")
    m = re.search(r"boundary=([^\s;]+)", ctype)
    if not m:
        raise ValueError("missing multipart boundary")
    boundary = m.group(1).strip().strip('"').encode("ascii")
    n = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(n)
    fields: dict[str, str] = {}
    files: dict[str, bytes] = {}
    parts = raw.split(b"--" + boundary)
    for part in parts:
        if not part or part in (b"--\r\n", b"--", b"\r\n"):
            continue
        if part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        header_blob, _, body = part.partition(b"\r\n\r\n")
        if body.endswith(b"\r\n"):
            body = body[:-2]
        headers = header_blob.decode("utf-8", errors="replace")
        name_m = re.search(r'name="([^"]+)"', headers)
        if not name_m:
            continue
        name = name_m.group(1)
        if "filename=" in headers:
            files[name] = body
        else:
            fields[name] = body.decode("utf-8", errors="replace")
    return fields, files


def _save_upload(filename: str, data: bytes) -> Path:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", filename or "model.stl")[:120]
    path = UPLOAD_ROOT / f"{uuid.uuid4().hex[:10]}_{safe}"
    path.write_bytes(data)
    return path


def _list_printers() -> list[dict[str, Any]]:
    from .slice.printers import PRINTERS

    out = []
    for key, spec in PRINTERS.items():
        out.append({
            "key": key,
            "display_name": spec.display_name,
            "bed_xy_mm": spec.bed_xy_mm,
            "bed_z_mm": spec.bed_z_mm,
            "backend": spec.backend,
            "notes": spec.notes,
        })
    return out


def _api_health() -> tuple[int, bytes, str]:
    return _json_bytes({
        "ok": True,
        "product": BRAND["product"],
        "version": __version__,
        "bind": "127.0.0.1",
        "tagline": BRAND["tagline"],
    })


def _api_printers() -> tuple[int, bytes, str]:
    return _json_bytes({"ok": True, "printers": _list_printers()})


def _api_cheatsheet() -> tuple[int, bytes, str]:
    return _json_bytes({
        "ok": True,
        "title": "Agent cheatsheet",
        "commands": [
            "forge slice model.stl --printer a1mini --dry-run",
            "forge slice model.stl --printer a2l -o out.gcode.3mf --auto-refit",
            "forge review out.gcode.3mf",
            "forge send out.gcode.3mf --dry-run",
            "forge send out.gcode.3mf --bed-confirmed",
            "forge slice-send model.stl --printer ad5x --bed-confirmed",
            "forge discover --save myprinter",
            "forge status",
        ],
    })


def _api_status(config_path: str | None) -> tuple[int, bytes, str]:
    try:
        from .config import build_adapters, load_config
        from .jobqueue import JobQueue

        cfg = load_config(config_path)
        adapters = build_adapters(cfg)
        queue_path = Path.home() / ".config" / "peoples-slicer" / "queue.json"
        jobs = []
        if queue_path.is_file():
            try:
                q = JobQueue(queue_path)
                jobs = list(getattr(q, "list", lambda: [])() or [])
            except Exception:
                jobs = []
        return _json_bytes({
            "ok": True,
            "configured_printers": list(adapters.keys()) if isinstance(adapters, dict) else len(adapters),
            "adapter_keys": list(adapters.keys()) if isinstance(adapters, dict) else [],
            "jobs": jobs[:20],
        })
    except Exception as e:
        return _json_bytes({"ok": False, "error": str(e)}, 500)


def _api_slice(body: dict[str, Any] | None = None, upload: Path | None = None) -> tuple[int, bytes, str]:
    from .slice import FitError, SliceError, slice_for

    body = body or {}
    model = upload
    if model is None:
        p = (body.get("path") or "").strip()
        if not p:
            return _json_bytes({"ok": False, "error": "model path or upload required"}, 400)
        model = Path(p).expanduser().resolve()
    if not model.is_file():
        return _json_bytes({"ok": False, "error": f"model not found: {model}"}, 400)

    printer = (body.get("printer") or "").strip()
    if not printer:
        return _json_bytes({"ok": False, "error": "printer required"}, 400)

    dry_run = bool(body.get("dry_run"))
    auto_refit = body.get("auto_refit")
    if auto_refit is None:
        auto_refit = True
    auto_refit = bool(auto_refit)
    output = body.get("output")

    try:
        result = slice_for(
            model,
            printer,
            output=output,
            dry_run=dry_run,
            auto_refit=auto_refit,
            timeout=int(body.get("timeout") or 900),
        )
    except FitError as e:
        return _json_bytes({"ok": False, "error": f"FIT: {e}", "kind": "fit"}, 422)
    except (SliceError, FileNotFoundError, KeyError, ValueError) as e:
        return _json_bytes({"ok": False, "error": str(e), "kind": "slice"}, 422)
    except Exception as e:
        return _json_bytes({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc(limit=6),
        }, 500)

    payload = {
        "ok": result.ok,
        "printer": result.printer,
        "backend": result.backend,
        "output": result.output,
        "source": str(model),
        "bounds": result.bounds,
        "estimates": getattr(result, "estimates", None),
        "scale": result.scale,
        "repetitions": result.repetitions,
        "detail": result.detail,
        "dry_run": dry_run,
    }
    job_id = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        _JOBS[job_id] = payload
    payload["job_id"] = job_id
    return _json_bytes(payload)


def _api_review(body: dict[str, Any]) -> tuple[int, bytes, str]:
    from .review import review_file

    path = (body.get("path") or body.get("file") or "").strip()
    if not path:
        return _json_bytes({"ok": False, "error": "path required"}, 400)
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return _json_bytes({"ok": False, "error": f"file not found: {p}"}, 400)
    try:
        report = review_file(str(p), printer=body.get("printer"))
    except Exception as e:
        return _json_bytes({"ok": False, "error": str(e)}, 500)
    blocking = bool(report.get("blocking"))
    return _json_bytes({"ok": not blocking, "blocking": blocking, "report": report}, 200 if not blocking else 422)


def _api_send(body: dict[str, Any], config_path: str | None) -> tuple[int, bytes, str]:
    from .config import build_adapters, load_config
    from .dispatcher import Dispatcher
    from .guardian import Guardian
    from .jobqueue import JobQueue
    from .store import JsonlStore

    path = (body.get("path") or body.get("file") or "").strip()
    if not path:
        return _json_bytes({"ok": False, "error": "path required"}, 400)
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return _json_bytes({"ok": False, "error": f"file not found: {p}"}, 400)

    dry_run = bool(body.get("dry_run"))
    bed = bool(body.get("bed_confirmed"))
    if dry_run:
        from .reader import classify_file
        try:
            info = classify_file(str(p))
            return _json_bytes({
                "ok": True,
                "dry_run": True,
                "result": {
                    "state": "dry_run",
                    "printer": info.printer,
                    "material": info.material,
                    "colors": info.colors,
                    "est_seconds": info.est_seconds,
                    "est_grams": info.est_grams,
                    "path": str(p),
                },
            })
        except Exception as e:
            return _json_bytes({"ok": False, "error": str(e)}, 500)

    if not bed:
        return _json_bytes({
            "ok": False,
            "error": "Live send requires bed_confirmed=true (physical bed clear). Use dry_run for a no-send check.",
            "kind": "guardian",
        }, 403)

    try:
        cfg = load_config(config_path)
        adapters = build_adapters(cfg)
        if not adapters:
            return _json_bytes({
                "ok": False,
                "error": "No printers configured. Run forge discover --save <key> or set FORGE_CONFIG / env credentials.",
            }, 400)
        cfg_dir = Path.home() / ".config" / "peoples-slicer"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        store = JsonlStore(cfg_dir / "events.jsonl")
        queue = JobQueue(cfg_dir / "queue.json")
        guardian = Guardian()
        dispatcher = Dispatcher(
            adapters=adapters, queue=queue, store=store, guardian=guardian
        )
        result = dispatcher.submit(str(p), bed_confirmed_clear=True)
        ok = result.get("state") in ("printing", "queued")
        return _json_bytes({"ok": ok, "dry_run": False, "result": result}, 200 if ok else 422)
    except Exception as e:
        return _json_bytes({"ok": False, "error": str(e), "trace": traceback.format_exc(limit=6)}, 500)


def make_handler(config_path: str | None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            # Quiet default; Studio is local.
            sys_stderr = __import__("sys").stderr
            print(f"[studio] {self.address_string()} {fmt % args}", file=sys_stderr)

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _static(self, rel: str) -> None:
            if ".." in rel or rel.startswith("/"):
                self._send(400, b"bad path", "text/plain")
                return
            path = (GUI_DIR / (rel or "index.html")).resolve()
            if not str(path).startswith(str(GUI_DIR.resolve())):
                self._send(403, b"forbidden", "text/plain")
                return
            if path.is_dir():
                path = path / "index.html"
            if not path.is_file():
                self._send(404, b"not found", "text/plain")
                return
            data = path.read_bytes()
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            self._send(200, data, ctype)

        def do_GET(self) -> None:  # noqa: N802
            u = urlparse(self.path)
            path = u.path
            if path == "/api/health":
                self._send(*_api_health())
                return
            if path == "/api/printers":
                self._send(*_api_printers())
                return
            if path == "/api/cheatsheet":
                self._send(*_api_cheatsheet())
                return
            if path == "/api/status":
                self._send(*_api_status(config_path))
                return
            if path.startswith("/api/"):
                self._send(*_json_bytes({"ok": False, "error": "not found"}, 404))
                return
            rel = path.lstrip("/") or "index.html"
            self._static(rel)

        def do_POST(self) -> None:  # noqa: N802
            u = urlparse(self.path)
            path = u.path
            try:
                if path == "/api/upload-slice":
                    fields, files = _parse_multipart(self)
                    blob = files.get("file") or files.get("model")
                    if not blob:
                        self._send(*_json_bytes({"ok": False, "error": "file field required"}, 400))
                        return
                    name = fields.get("filename") or "model.stl"
                    saved = _save_upload(name, blob)
                    body = {
                        "printer": fields.get("printer") or "",
                        "dry_run": (fields.get("dry_run") or "").lower() in ("1", "true", "yes"),
                        "auto_refit": (fields.get("auto_refit") or "true").lower() not in ("0", "false", "no"),
                    }
                    self._send(*_api_slice(body, upload=saved))
                    return

                body = _read_json(self)
                if path == "/api/slice":
                    self._send(*_api_slice(body))
                    return
                if path == "/api/review":
                    self._send(*_api_review(body))
                    return
                if path == "/api/send":
                    self._send(*_api_send(body, config_path))
                    return
                self._send(*_json_bytes({"ok": False, "error": "not found"}, 404))
            except ValueError as e:
                self._send(*_json_bytes({"ok": False, "error": str(e)}, 400))
            except Exception as e:
                self._send(*_json_bytes({
                    "ok": False,
                    "error": str(e),
                    "trace": traceback.format_exc(limit=8),
                }, 500))

    return Handler


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: str | None = None,
    open_browser: bool = True,
) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Studio GUI must bind to localhost only")
    if not GUI_DIR.is_dir():
        raise FileNotFoundError(f"GUI assets missing: {GUI_DIR}")

    handler = make_handler(config_path)
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"{BRAND['product']} Studio v{__version__}")
    print(f"  open → {url}")
    print(f"  local only · agent CLI still: forge slice | send | review")
    print("  Ctrl+C to stop")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStudio stopped.")
    finally:
        httpd.server_close()
