"""Load printer config from environment or an optional JSON file."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_config(path: str | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = {"printers": {}}
    config_path = path or os.environ.get("FORGE_CONFIG")
    if config_path and Path(config_path).exists():
        cfg.update(json.loads(Path(config_path).read_text()))

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
    return cfg


def build_adapters(cfg: dict[str, Any]) -> dict:
    from .adapters.ad5x import AD5XAdapter
    from .adapters.bambu import BambuAdapter
    from .adapters.klipper import KlipperAdapter

    adapters = {}
    for key, spec in cfg.get("printers", {}).items():
        kind = spec.get("type", key)
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