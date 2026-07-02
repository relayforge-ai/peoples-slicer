"""FlashForge AD5X adapter — 8898 HTTP status + 8899 file send + multicolor IFS keystone.

Protocol reverse-engineered by GhostTypes/ff-5mp-api-py (MIT).
"""
from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
import zipfile
from typing import Callable

DetailFetcher = Callable[[], dict]
ApiPoster = Callable[[str, dict], dict]


class AD5XAdapter:
    key = "ad5x"

    def __init__(
        self,
        host: str,
        serial: str,
        checkcode: str,
        *,
        gcode_port: int = 8899,
        http_port: int = 8898,
        detail_fetcher: DetailFetcher | None = None,
        api_poster: ApiPoster | None = None,
    ):
        if not host or not serial or not checkcode:
            raise ValueError("host, serial, and checkcode are required")
        self.host = host
        self.serial = serial
        self.checkcode = checkcode
        self.gcode_port = gcode_port
        self.http_port = http_port
        self._detail_fetcher = detail_fetcher
        self._api_poster = api_poster

    @staticmethod
    def _map_status(detail_status: str | None) -> str:
        # "ready" and "completed" (finished, awaiting bed-clear) both mean the printer
        # can accept the next job — otherwise a completed printer stalls the queue forever.
        s = (detail_status or "").lower()
        return "idle" if s in ("ready", "completed") else "printing"

    @staticmethod
    def _remote_name(path: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(path))

    def _auth_body(self, extra: dict | None = None) -> dict:
        body = {"serialNumber": self.serial, "checkCode": self.checkcode}
        if extra:
            body.update(extra)
        return body

    def _api(self, path: str, body: dict) -> dict:
        if self._api_poster is not None:
            return self._api_poster(path, body)
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"http://{self.host}:{self.http_port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.load(resp)

    def detail(self) -> dict:
        if self._detail_fetcher is not None:
            return self._detail_fetcher()
        return self._api("/detail", self._auth_body()).get("detail", {})

    def status(self) -> str:
        try:
            return self._map_status(self.detail().get("status"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            return "offline"

    @staticmethod
    def _recv(sock: socket.socket, timeout: float = 8.0) -> bytes:
        sock.settimeout(timeout)
        buf = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if buf.rstrip().endswith(b"ok"):
                    break
        except TimeoutError:
            pass
        return buf

    def _cmd(self, sock: socket.socket, command: str, timeout: float = 8.0) -> bytes:
        sock.sendall(("~" + command + "\r\n").encode())
        return self._recv(sock, timeout)

    def _is_multicolor(self, gcode_path: str) -> bool:
        # A multicolor AD5X job is a .3mf (zip) whose gcode lists >1 filament_colour.
        if not zipfile.is_zipfile(gcode_path):
            return False
        try:
            return len(self.tool_colors(gcode_path)) > 1
        except Exception:
            return False

    def send(self, gcode_path: str, start: bool = True) -> str:
        remote = self._remote_name(gcode_path)
        multicolor = self._is_multicolor(gcode_path)
        with open(gcode_path, "rb") as fh:
            data = fh.read()

        # Both single- and multi-color first upload the file over the 8899 socket.
        sock = socket.create_connection((self.host, self.gcode_port), timeout=8)
        try:
            self._cmd(sock, "M601 S1")
            self._cmd(sock, f"M28 {len(data)} 0:/user/{remote}")
            sock.sendall(data)
            self._cmd(sock, "M29")
            # Single-color start: M23 SELECTS the file, M6030 actually STARTS it — both required.
            if start and not multicolor:
                self._cmd(sock, f"M23 0:/user/{remote}")
                self._cmd(sock, f'M6030 ":/user/{remote}"')
        finally:
            sock.close()

        # Multicolor keystone: after upload, start via /printGcode carrying the IFS
        # useMatlStation + materialMappings map — else the AD5X silently prints mono.
        if multicolor:
            self.send_multicolor(gcode_path, file_on_printer=remote, fire=start)
        return remote

    @staticmethod
    def tool_colors(local_3mf: str) -> list[str]:
        with zipfile.ZipFile(local_3mf) as zf:
            gc_name = next(n for n in zf.namelist() if n.endswith("plate_1.gcode"))
            with zf.open(gc_name) as fh:
                for raw in fh:
                    line = raw.decode("utf-8", "replace")
                    if line.startswith("; filament_colour"):
                        return [
                            c.strip()
                            for c in line.split("=", 1)[1].strip().split(";")
                            if c.strip()
                        ]
        return []

    @staticmethod
    def _rgb(color: str) -> tuple[int, int, int]:
        c = color.lstrip("#")[:6]
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def build_mappings(tool_cols: list[str], slots: list[dict]) -> list[dict]:
        # Only match against slots that actually have filament loaded; an empty
        # slot whose stale color happens to be nearest must never win the match.
        loaded = [s for s in slots if s.get("hasFilament", True)] or slots
        maps: list[dict] = []
        for tid, tc in enumerate(tool_cols):
            tr = AD5XAdapter._rgb(tc)
            best = min(
                loaded,
                key=lambda sl: sum(
                    (a - b) ** 2
                    for a, b in zip(tr, AD5XAdapter._rgb(sl.get("materialColor", "#000000")))
                ),
            )
            maps.append(
                {
                    "toolId": tid,
                    "slotId": best["slotId"],
                    "materialName": best.get("materialName", "PLA"),
                    "toolMaterialColor": tc if tc.startswith("#") else "#" + tc,
                    "slotMaterialColor": best.get("materialColor", "#000000"),
                }
            )
        return maps

    def clear_completed(self) -> None:
        self._api(
            "/control",
            {
                **self._auth_body(),
                "payload": {"cmd": "stateCtrl_cmd", "args": {"action": "setClearPlatform"}},
            },
        )

    def send_multicolor(
        self,
        gcode_path: str,
        *,
        file_on_printer: str | None = None,
        leveling: bool = True,
        fire: bool = True,
    ) -> dict | None:
        detail = self.detail()
        slots = detail.get("matlStationInfo", {}).get("slotInfos", [])
        if not slots:
            raise RuntimeError("No IFS slots reported — material station not ready")

        tool_cols = self.tool_colors(gcode_path)
        if not tool_cols:
            raise RuntimeError("No filament_colour in gcode — not a multicolor slice?")

        maps = self.build_mappings(tool_cols, slots)
        remote = file_on_printer or self._remote_name(gcode_path)
        payload = {
            **self._auth_body(),
            "fileName": remote,
            "levelingBeforePrint": leveling,
            "firstLayerInspection": False,
            "flowCalibration": False,
            "timeLapseVideo": False,
            "useMatlStation": True,
            "gcodeToolCnt": len(maps),
            "materialMappings": maps,
        }
        if not fire:
            return payload

        if detail.get("status") == "completed":
            self.clear_completed()
            time.sleep(3)

        return self._api("/printGcode", payload)