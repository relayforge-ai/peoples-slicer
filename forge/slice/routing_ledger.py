"""REL-599 — record per-SKU routing facts (fit failures are not slicer crashes).

When a model is physically larger than the target bed (e.g. 256 mm design on A1 mini
180 mm), we log a durable fact so Jules can route to a2l/ad5x instead of retrying forever.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path(
    os.environ.get(
        "FORGE_ROUTING_LEDGER",
        str(Path.home() / ".forge" / "routing_facts.json"),
    )
)


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    path = Path(path or DEFAULT_LEDGER)
    if not path.exists():
        return {"facts": [], "by_sku": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"facts": [], "by_sku": {}}


def record_fit_failure(
    *,
    model: str | Path,
    printer: str,
    message: str,
    bounds: dict[str, float] | None = None,
    sku: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Append a routing fact and return the written ledger snapshot."""
    ledger_path = Path(path or DEFAULT_LEDGER)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    data = load_ledger(ledger_path)
    model_p = Path(model)
    key = sku or model_p.stem
    fact = {
        "sku": key,
        "model": str(model_p),
        "printer": printer,
        "kind": "does_not_fit",
        "message": message,
        "bounds": bounds,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "routing": "try larger bed (a2l 256 / ad5x 220) or --auto-refit",
    }
    data.setdefault("facts", []).append(fact)
    by = data.setdefault("by_sku", {})
    by[key] = fact
    ledger_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return fact


def is_known_misfit(sku_or_stem: str, printer: str, path: Path | None = None) -> bool:
    data = load_ledger(path)
    fact = (data.get("by_sku") or {}).get(sku_or_stem)
    if not fact:
        return False
    return fact.get("printer") == printer and fact.get("kind") == "does_not_fit"
