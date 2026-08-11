"""Load printer config from environment or an optional JSON file."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load the forge config, layering environment overrides over a JSON file.

    The config source is ``path`` if given, else the ``FORGE_CONFIG`` env var.
    A missing (or unset) file is not an error — the base ``{"printers": {}}`` is
    used — but a file that exists and is *not* a valid JSON object raises a clear
    :class:`ValueError` naming the file rather than leaking a bare
    ``JSONDecodeError`` (mirroring :func:`forge.discover.merge_into_config`).

    After the file is loaded, the ``AD5X_HOST`` / ``BAMBU_HOST`` / ``MOONRAKER_URL``
    / ``KOBRA_MOONRAKER_URL`` env vars (with their optional credential companions)
    add or replace the printer entries keyed ``"ad5x"`` / ``"bambu"`` / ``"ender"``
    / ``"kobra3max"`` respectively, so an env var wins over a same-key file entry.
    This lets a single exported host bring a printer online without a config file
    at all. No default/fallback host is baked in here for any printer — this repo
    is public, so every LAN address has to come from the environment, never a
    hardcoded literal.

    Returns the config dict — always with a ``"printers"`` mapping — ready to
    hand to :func:`build_adapters`.
    """
    cfg: dict[str, Any] = {"printers": {}}
    config_path = path or os.environ.get("FORGE_CONFIG")
    if config_path and Path(config_path).exists():
        try:
            loaded = json.loads(Path(config_path).read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed forge config JSON: {config_path}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"forge config must be a JSON object: {config_path}")
        cfg.update(loaded)

    printers = cfg.setdefault("printers", {})
    if os.environ.get("AD5X_HOST"):
        printers["ad5x"] = {
            "type": "ad5x",
            "host": os.environ["AD5X_HOST"],
            "serial": os.environ.get("AD5X_SERIAL", ""),
            "checkcode": os.environ.get("AD5X_CHECKCODE", ""),
        }
    if os.environ.get("BAMBU_HOST"):
        printers["bambu"] = {
            "type": "bambu",
            "host": os.environ["BAMBU_HOST"],
            "access_code": os.environ.get("BAMBU_ACCESS_CODE", ""),
            "serial": os.environ.get("BAMBU_SERIAL", ""),
        }
    if os.environ.get("MOONRAKER_URL"):
        printers["ender"] = {
            "type": "klipper",
            "moonraker_url": os.environ["MOONRAKER_URL"],
        }
    if os.environ.get("KOBRA_MOONRAKER_URL"):
        printers["kobra3max"] = {
            "type": "klipper",
            "moonraker_url": os.environ["KOBRA_MOONRAKER_URL"],
        }
    return cfg


def build_adapters(cfg: dict[str, Any]) -> dict:
    """Instantiate a printer adapter for each entry in ``cfg["printers"]``.

    The spec's ``type`` selects the adapter; unrecognized types are skipped.
    A spec missing a required host/credential field raises a :class:`ValueError`
    naming the offending printer and field, instead of leaking a bare
    ``KeyError`` from deep inside adapter construction.
    """
    from .adapters.ad5x import AD5XAdapter
    from .adapters.bambu import BambuAdapter
    from .adapters.klipper import KlipperAdapter

    required_fields = {
        "ad5x": ("host", "serial", "checkcode"),
        "bambu": ("host", "access_code", "serial"),
        "klipper": ("moonraker_url",),
        "ender": ("moonraker_url",),
    }

    adapters = {}
    for key, spec in cfg.get("printers", {}).items():
        kind = spec.get("type", key)
        for name in required_fields.get(kind, ()):
            if name not in spec:
                raise ValueError(
                    f"printer {key!r} ({kind}) is missing required field {name!r}"
                )
        if kind == "ad5x":
            adapters[key] = AD5XAdapter(
                host=spec["host"],
                serial=spec["serial"],
                checkcode=spec["checkcode"],
            )
        elif kind == "bambu":
            adapters[key] = BambuAdapter(
                host=spec["host"],
                access_code=spec["access_code"],
                serial=spec["serial"],
            )
        elif kind in ("klipper", "ender"):
            adapters[key] = KlipperAdapter(moonraker_url=spec["moonraker_url"])
    return adapters