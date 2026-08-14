"""Bambu A2L adapter — implicit FTPS upload + MQTT start with AMS mapping.

Uses implicit FTPS on :990 (TLS from connect) and MQTT on :8883.
Bambu ships a broken cert chain; CERT_NONE is standard for LAN integrations.
"""
from __future__ import annotations

import json
import os
import ssl
import ftplib
import threading
import zipfile
from pathlib import Path
from typing import Callable, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - optional until bambu extra installed
    mqtt = None  # type: ignore

MqttPublisher = Callable[[dict, bool], Optional[dict]]
FtpsUploader = Callable[[str, str], str]
StateFetcher = Callable[[], dict]


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """Bambu uses implicit FTPS on :990 (TLS from connect)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value


class BambuAdapter:
    key = "bambu"

    def __init__(
        self,
        host: str,
        access_code: str,
        serial: str,
        *,
        ftps_port: int = 990,
        mqtt_port: int = 8883,
        upload_retries: int = 3,
        mqtt_publisher: MqttPublisher | None = None,
        ftps_uploader: FtpsUploader | None = None,
        state_fetcher: StateFetcher | None = None,
    ):
        if not host or not access_code or not serial:
            raise ValueError("host, access_code, and serial are required")
        self.host = host
        self.access_code = access_code
        self.serial = serial
        self.ftps_port = ftps_port
        self.mqtt_port = mqtt_port
        self.upload_retries = max(1, upload_retries)
        self._mqtt_publisher = mqtt_publisher
        self._ftps_uploader = ftps_uploader
        self._state_fetcher = state_fetcher
        self._seq = 0
        self.topic_pub = f"device/{serial}/request"
        self.topic_sub = f"device/{serial}/report"

    def _next_seq(self) -> str:
        self._seq += 1
        return str(self._seq)

    @staticmethod
    def _tls_context() -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    @staticmethod
    def _rgb(color: str) -> tuple[int, int, int]:
        c = color.lstrip("#")[:6]
        if len(c) < 6:
            return (0, 0, 0)
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _mqtt_color_to_hex(color: str) -> str:
        # Bambu MQTT reports RRGGBBAA; gcode headers use #RRGGBB.
        c = (color or "").strip()
        if not c or c == "00000000":
            return "#000000"
        if c.startswith("#"):
            return c
        return "#" + c[:6]

    @staticmethod
    def tool_colors(gcode_path: str) -> list[str]:
        path = Path(gcode_path)
        if path.suffix == ".3mf" or path.name.endswith(".gcode.3mf"):
            with zipfile.ZipFile(gcode_path) as zf:
                gc_name = next(n for n in zf.namelist() if n.endswith("plate_1.gcode"))
                text = zf.read(gc_name).decode("utf-8", errors="replace")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("; filament_colour"):
                return [
                    c.strip()
                    for c in line.split("=", 1)[1].strip().split(";")
                    if c.strip()
                ]
        return []

    @staticmethod
    def parse_ams_trays(ams_state: dict) -> list[dict]:
        """Flatten Bambu's nested AMS report into one dict per tray.

        Each AMS unit holds four trays, so a tray's global slot index — the value
        an ``ams_mapping`` entry references — is ``unit_id * 4 + tray_id``.

        Returns one ``{"slot": int, "color": "#RRGGBB", "loaded": bool}`` per tray
        in report order, where ``loaded`` marks slots that actually hold filament
        (so an empty slot is never a color-match candidate in ``build_ams_mapping``).
        """
        trays: list[dict] = []
        for ams_unit in ams_state.get("ams", []):
            ams_id = int(ams_unit.get("id", 0))
            for tray in ams_unit.get("tray", []):
                tray_id = tray.get("id")
                if tray_id is None:
                    continue
                tray_type = (tray.get("tray_type") or "").strip()
                color = BambuAdapter._mqtt_color_to_hex(tray.get("tray_color", ""))
                # Empty AMS slots report only {"id": "N"} with no tray_type — not by color.
                loaded = bool(tray_type)
                trays.append(
                    {
                        "slot": ams_id * 4 + int(tray_id),
                        "color": color,
                        "loaded": loaded,
                    }
                )
        return trays

    @staticmethod
    def build_ams_mapping(tool_cols: list[str], trays: list[dict]) -> list[int]:
        loaded = [t for t in trays if t.get("loaded")]
        if not loaded:
            raise RuntimeError("No loaded AMS trays — cannot map multicolor job")
        mapping: list[int] = []
        for tc in tool_cols:
            tr = BambuAdapter._rgb(tc)
            best = min(
                loaded,
                key=lambda sl: sum(
                    (a - b) ** 2 for a, b in zip(tr, BambuAdapter._rgb(sl["color"]))
                ),
            )
            mapping.append(best["slot"])
        return mapping

    def _verify_remote_size(self, ftp: ftplib.FTP_TLS, remote_name: str, expected: int) -> None:
        remote_path = f"/{remote_name}"
        try:
            remote_size = ftp.size(remote_path)
        except ftplib.error_perm:
            lines: list[str] = []
            ftp.retrlines(f"LIST {remote_path}", lines.append)
            remote_size = None
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and parts[-1].endswith(remote_name):
                    remote_size = int(parts[4])
                    break
            if remote_size is None:
                raise RuntimeError(f"FTPS upload verify failed: cannot stat {remote_path}")
        if remote_size != expected:
            raise RuntimeError(
                f"FTPS upload size mismatch for {remote_name}: local={expected} remote={remote_size}"
            )

    def _upload(self, local_path: str, remote_name: str) -> str:
        if self._ftps_uploader is not None:
            return self._ftps_uploader(local_path, remote_name)

        expected = os.path.getsize(local_path)
        last_err: Exception | None = None
        for _ in range(self.upload_retries):
            ftp: ftplib.FTP_TLS | None = None
            try:
                ctx = self._tls_context()
                ftp = ImplicitFTP_TLS(context=ctx)
                ftp.connect(self.host, self.ftps_port, timeout=120)
                ftp.login("bblp", self.access_code)
                ftp.prot_p()
                with open(local_path, "rb") as fh:
                    ftp.storbinary(f"STOR /{remote_name}", fh)
                self._verify_remote_size(ftp, remote_name, expected)
                ftp.quit()
                return f"/{remote_name}"
            except Exception as exc:  # noqa: BLE001 - retry landmine
                last_err = exc
                # Bambu's FTPS control channel allows only one session at a time — an
                # abandoned connection from a failed attempt can block the very retry
                # this loop exists to make. quit() needs a working channel (which may be
                # exactly what just broke), so close() unconditionally instead.
                if ftp is not None:
                    try:
                        ftp.close()
                    except Exception:  # noqa: BLE001 - best-effort cleanup
                        pass
        raise RuntimeError(f"FTPS upload failed after {self.upload_retries} tries") from last_err

    def _publish(self, payload: dict, wait_reply: bool = False) -> Optional[dict]:
        if self._mqtt_publisher is not None:
            return self._mqtt_publisher(payload, wait_reply)
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required for BambuAdapter (pip install paho-mqtt)")

        result: list[Optional[dict]] = [None]
        got_reply = threading.Event()

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set("bblp", self.access_code)
        client.tls_set_context(self._tls_context())
        connected = threading.Event()

        def on_connect(c, _u, _f, rc, _p=None):
            ok = (rc == 0) if isinstance(rc, int) else (str(rc) == "Success")
            if ok:
                c.subscribe(self.topic_sub)
                connected.set()

        if wait_reply:
            def on_message(_c, _u, msg):
                try:
                    data = json.loads(msg.payload)
                    if "print" in data:
                        result[0] = data
                        got_reply.set()
                except json.JSONDecodeError:
                    pass

            client.on_message = on_message

        client.on_connect = on_connect
        client.connect(self.host, self.mqtt_port, keepalive=30)
        client.loop_start()
        if not connected.wait(8):
            client.loop_stop()
            client.disconnect()
            return None

        client.publish(self.topic_pub, json.dumps(payload))
        if wait_reply:
            got_reply.wait(10)

        client.loop_stop()
        client.disconnect()
        return result[0]

    def _fetch_print_state(self) -> dict:
        if self._state_fetcher is not None:
            return self._state_fetcher()
        result: list[dict] = [{}]
        got = threading.Event()
        if mqtt is None:
            return {}

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set("bblp", self.access_code)
        client.tls_set_context(self._tls_context())
        connected = threading.Event()

        def on_connect(c, _u, _f, rc, _p=None):
            ok = (rc == 0) if isinstance(rc, int) else (str(rc) == "Success")
            if ok:
                c.subscribe(self.topic_sub)
                connected.set()

        def on_message(_c, _u, msg):
            try:
                data = json.loads(msg.payload)
                if "print" in data:
                    result[0] = data["print"]
                    got.set()
            except json.JSONDecodeError:
                pass

        client.on_message = on_message
        client.on_connect = on_connect
        client.connect(self.host, self.mqtt_port, keepalive=30)
        client.loop_start()
        if not connected.wait(8):
            client.loop_stop()
            client.disconnect()
            return {}

        client.publish(
            self.topic_pub,
            json.dumps(
                {
                    "pushing": {
                        "sequence_id": self._next_seq(),
                        "command": "start",
                        "version": 1,
                        "push_target": 1,
                    }
                }
            ),
        )
        got.wait(8)
        client.loop_stop()
        client.disconnect()
        return result[0]

    def status(self) -> str:
        try:
            state = self._fetch_print_state()
            if not state:
                return "offline"
            gcode_state = state.get("gcode_state", "IDLE")
            if gcode_state in ("RUNNING", "PAUSE"):
                return "printing"
            return "idle"
        except Exception:  # noqa: BLE001
            return "offline"

    def send(
        self,
        gcode_path: str,
        start: bool = True,
        *,
        ams_mapping: list[int] | None = None,
        subtask_name: str | None = None,
    ) -> str:
        path = Path(gcode_path)
        if path.suffix == ".3mf" or path.name.endswith(".gcode.3mf"):
            with zipfile.ZipFile(gcode_path) as zf:
                if not any(n.endswith("plate_1.gcode") for n in zf.namelist()):
                    raise ValueError("no Metadata/plate_1.gcode in 3mf — not sliced?")

        remote_name = path.name
        remote = self._upload(gcode_path, remote_name)
        if not start:
            return remote_name

        tool_cols = self.tool_colors(gcode_path)
        use_ams = False
        if ams_mapping is not None:
            mapping = ams_mapping
            use_ams = bool(mapping)
        else:
            if tool_cols:
                try:
                    state = self._fetch_print_state()
                except Exception:
                    if len(tool_cols) > 1:
                        raise
                    state = {}
                trays = self.parse_ams_trays(state.get("ams", {}))
                if trays:
                    mapping = self.build_ams_mapping(tool_cols, trays)
                    use_ams = True
                elif len(tool_cols) > 1:
                    raise RuntimeError("No AMS trays reported — cannot map multicolor job")
                else:
                    # A one-tool job can still run from an external spool when
                    # no AMS is attached. If AMS trays do exist, the branch
                    # above maps the 3MF's approved/default color to one of
                    # them instead of silently forcing external-spool mode.
                    mapping = [0]
            else:
                mapping = [0]
        is_bundle = path.suffix == ".3mf" or path.name.endswith(".gcode.3mf")
        payload = {
            "print": {
                "sequence_id": self._next_seq(),
                "command": "project_file",
                "param": "Metadata/plate_1.gcode" if is_bundle else remote_name.lstrip("/"),
                "url": f"ftp://{remote}",
                "subtask_name": subtask_name or path.stem,
                # A1-mini-class firmware replies "success" but never starts a
                # project_file without these ids; A2L accepts either way.
                # Verified live on telchar_2's maiden print, 2026-07-03.
                "project_id": "0",
                "profile_id": "0",
                "task_id": "0",
                "subtask_id": "0",
                "use_ams": use_ams,
                "ams_mapping": mapping if use_ams else [0],
                "bed_type": "auto",
                "bed_leveling": True,
                "flow_cali": False,
                "vibration_cali": True,
                "layer_inspect": False,
                "timelapse": False,
            }
        }
        self._publish(payload, wait_reply=True)
        return remote_name
