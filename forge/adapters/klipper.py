"""Klipper / Moonraker adapter — upload + print/start with firmware_restart recovery."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

HttpPoster = Callable[[str, str, bytes | None, dict | None], dict]
StatusFetcher = Callable[[], dict]


class KlipperAdapter:
    """Drive a Klipper printer through its Moonraker HTTP API.

    Implements the :class:`~forge.adapters.base.Adapter` contract (``status`` +
    ``send``) for any Moonraker host, with two deliberate robustness behaviors
    that keep an unreliable LAN from surprising the caller:

    - ``status()`` never raises: any network failure (unreachable host, timeout,
      malformed JSON, HTTP error) is reported as ``"offline"``, so the dispatcher
      treats an unreachable printer as simply not-idle rather than crashing.
    - upload and print-start each retry **once** through a ``firmware_restart()``
      when Moonraker reports "Lost communication with MCU" — the common
      recoverable stall on these boards — instead of failing the job outright.

    ``http_poster`` / ``status_fetcher`` are injection seams for tests; when
    left unset the adapter talks to ``moonraker_url`` over real HTTP.
    """

    key = "ender"

    def __init__(
        self,
        moonraker_url: str,
        *,
        restart_wait_s: float = 13.0,
        http_poster: HttpPoster | None = None,
        status_fetcher: StatusFetcher | None = None,
    ):
        if not moonraker_url:
            raise ValueError("moonraker_url is required")
        self.base = moonraker_url.rstrip("/")
        self.restart_wait_s = restart_wait_s
        self._http_poster = http_poster
        self._status_fetcher = status_fetcher

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict | None = None,
    ) -> dict:
        if self._http_poster is not None:
            return self._http_poster(method, path, data, headers)

        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers=headers or {},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", "replace")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(err_body or str(exc)) from exc

    def _printer_state(self) -> dict:
        if self._status_fetcher is not None:
            return self._status_fetcher()
        return self._request("GET", "/printer/objects/query?print_stats&webhooks")

    def status(self) -> str:
        try:
            data = self._printer_state()
            result = data.get("result", {}).get("status", {})
            state = result.get("print_stats", {}).get("state", "standby")
            webhook = result.get("webhooks", {}).get("state", "ready")
            if webhook not in ("ready", "startup"):
                return "offline"
            if state in ("printing", "paused"):
                return "printing"
            return "idle"
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError):
            return "offline"

    def firmware_restart(self) -> None:
        self._request("POST", "/printer/firmware_restart")
        time.sleep(self.restart_wait_s)

    def _upload(self, gcode_path: str) -> str:
        filename = os.path.basename(gcode_path)
        boundary = "forge-klipper-boundary"
        with open(gcode_path, "rb") as fh:
            file_data = fh.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        try:
            self._request("POST", "/server/files/upload", data=body, headers=headers)
        except RuntimeError as exc:
            if "Lost communication with MCU" in str(exc):
                self.firmware_restart()
                self._request("POST", "/server/files/upload", data=body, headers=headers)
            else:
                raise
        return filename

    def _start(self, filename: str) -> None:
        query = urllib.parse.urlencode({"filename": filename})
        try:
            self._request("POST", f"/printer/print/start?{query}")
        except RuntimeError as exc:
            if "Lost communication with MCU" in str(exc):
                self.firmware_restart()
                self._request("POST", f"/printer/print/start?{query}")
            else:
                raise

    def send(self, gcode_path: str, start: bool = True) -> str:
        filename = self._upload(gcode_path)
        if start:
            self._start(filename)
        return filename