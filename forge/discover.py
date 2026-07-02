"""LAN discovery — fingerprint printers on the local network.

Pure stdlib: socket port probes + lightweight HTTP fingerprints. Credentials are
entered once and persisted via :func:`merge_into_config`.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

PROBE_TIMEOUT = float(os.environ.get("FORGE_DISCOVER_TIMEOUT", "1.5"))


@dataclass
class DiscoveredPrinter:
    host: str
    kind: str
    model: str = ""
    port: int = 0
    needs_credentials: bool = True
    detail: dict = field(default_factory=dict)


HostProber = Callable[[str], list[DiscoveredPrinter]]


def _port_open(host: str, port: int, timeout: float = PROBE_TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_json(url: str, *, method: str = "GET", data: bytes | None = None, timeout: float = PROBE_TIMEOUT) -> dict | None:
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return json.loads(body) if body else {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def probe_moonraker(host: str, port: int = 7125) -> DiscoveredPrinter | None:
    if not _port_open(host, port):
        return None
    info = _http_json(f"http://{host}:{port}/server/info")
    if not info or info.get("result", {}).get("klippy_state") is None:
        return None
    hostname = info.get("result", {}).get("hostname", "")
    return DiscoveredPrinter(
        host=host,
        kind="klipper",
        model=hostname or "Klipper (Moonraker)",
        port=port,
        needs_credentials=False,
        detail={"moonraker_url": f"http://{host}:{port}"},
    )


def probe_ad5x(host: str, http_port: int = 8898) -> DiscoveredPrinter | None:
    if not _port_open(host, http_port):
        return None
    # Unauthenticated /detail returns an error JSON — still proves AD5X shape.
    body = _http_json(
        f"http://{host}:{http_port}/detail",
        method="POST",
        data=b"{}",
    )
    if body is None:
        return None
    if "detail" in body or "serialNumber" in str(body).lower() or "checkcode" in str(body).lower():
        model = ""
        if isinstance(body.get("detail"), dict):
            model = body["detail"].get("machineName") or body["detail"].get("model") or ""
        return DiscoveredPrinter(
            host=host,
            kind="ad5x",
            model=model or "FlashForge AD5X",
            port=http_port,
            needs_credentials=True,
            detail={"http_port": http_port, "gcode_port": 8899},
        )
    return None


def probe_bambu(host: str, ftps_port: int = 990, mqtt_port: int = 8883) -> DiscoveredPrinter | None:
    # Bambu exposes implicit FTPS + LAN MQTT; either open port is a strong signal.
    if not (_port_open(host, ftps_port) or _port_open(host, mqtt_port)):
        return None
    port = ftps_port if _port_open(host, ftps_port) else mqtt_port
    return DiscoveredPrinter(
        host=host,
        kind="bambu",
        model="Bambu Lab (LAN)",
        port=port,
        needs_credentials=True,
        detail={"ftps_port": ftps_port, "mqtt_port": mqtt_port},
    )


def probe_host(host: str) -> list[DiscoveredPrinter]:
    """Run all fingerprints against one host. Multiple hits are possible (rare)."""
    found: list[DiscoveredPrinter] = []
    for fn in (probe_moonraker, probe_ad5x, probe_bambu):
        hit = fn(host)
        if hit is not None:
            found.append(hit)
    return found


def scan_hosts(hosts: list[str], prober: HostProber | None = None) -> list[DiscoveredPrinter]:
    probe = prober or probe_host
    results: list[DiscoveredPrinter] = []
    for host in hosts:
        results.extend(probe(host))
    return results


def iter_subnet_hosts(cidr: str) -> list[str]:
    net = ipaddress.ip_network(cidr, strict=False)
    return [str(ip) for ip in net.hosts()]


def default_subnet() -> str:
    """Best-effort local /24 from env or a common studio default."""
    return os.environ.get("FORGE_DISCOVER_SUBNET", "192.168.4.0/24")


def scan_subnet(cidr: str | None = None, prober: HostProber | None = None) -> list[DiscoveredPrinter]:
    return scan_hosts(iter_subnet_hosts(cidr or default_subnet()), prober=prober)


def merge_into_config(
    printer_key: str,
    spec: dict,
    config_path: str | None = None,
) -> dict:
    """Merge a discovered printer spec into the forge config JSON."""
    path = Path(config_path or os.path.expanduser(os.environ.get("FORGE_CONFIG", "~/.forge_config.json")))
    cfg: dict = {"printers": {}}
    if path.exists():
        loaded = json.loads(path.read_text())
        if isinstance(loaded, dict):
            cfg.update(loaded)
    printers = cfg.setdefault("printers", {})
    printers[printer_key] = spec
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


def printer_config_entry(found: DiscoveredPrinter, credentials: dict | None = None) -> dict:
    creds = credentials or {}
    if found.kind == "klipper":
        return {
            "type": "klipper",
            "moonraker_url": creds.get("moonraker_url") or found.detail.get("moonraker_url"),
        }
    if found.kind == "ad5x":
        return {
            "type": "ad5x",
            "host": found.host,
            "serial": creds.get("serial", ""),
            "checkcode": creds.get("checkcode", ""),
        }
    if found.kind == "bambu":
        return {
            "type": "bambu",
            "host": found.host,
            "access_code": creds.get("access_code", ""),
            "serial": creds.get("serial", ""),
        }
    raise ValueError(f"unsupported printer kind: {found.kind}")


def to_json(found: list[DiscoveredPrinter]) -> str:
    return json.dumps([asdict(x) for x in found], indent=2)