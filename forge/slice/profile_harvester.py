"""REL-600 — harvest Orca (and optional Bambu) vendor profile trees.

Orca ships dozens of vendor packs under ``resources/profiles/<Vendor>/``.
We index name → path + type so forge.slice can resolve inherits without
hardcoding, and so a 3×/wk cron can detect upstream profile drift.

Does **not** download anything by default — harvests the installed tree only.
Upstream AppImage refresh is a separate step (see ``scripts/update_orca_profiles.sh``).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ORCA_PROFILES = Path(
    os.environ.get(
        "ORCA_PROFILES",
        str(Path.home() / "orcaslicer" / "squashfs-root" / "resources" / "profiles"),
    )
)
DEFAULT_BAMBU_PROFILES = Path(
    os.environ.get(
        "BAMBU_PROFILES",
        str(Path(__file__).resolve().parent / "vendor_profiles" / "BBL"),
    )
)
DEFAULT_MANIFEST = Path(
    os.environ.get(
        "PROFILE_HARVEST_MANIFEST",
        str(Path.home() / ".forge" / "harvest" / "profile_manifest.json"),
    )
)

SKIP_NAMES = {
    "blacklist.json",
    "cli_config.json",
    "check_unused_setting_id.py",
    "check_duplicated_setting_id.py",
}


@dataclass
class ProfileRecord:
    name: str
    path: str
    type: str  # machine | process | filament | unknown
    vendor: str
    inherits: str | None
    sha256: str
    source: str  # orca | bambu | foundry


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _guess_type(data: dict[str, Any], path: Path) -> str:
    t = (data.get("type") or "").lower()
    if t in {"machine", "process", "filament"}:
        return t
    # path heuristics
    parts = {p.lower() for p in path.parts}
    if "machine" in parts:
        return "machine"
    if "process" in parts:
        return "process"
    if "filament" in parts:
        return "filament"
    return "unknown"


def harvest_tree(
    root: Path,
    *,
    source: str,
    vendor_hint: str | None = None,
) -> list[ProfileRecord]:
    """Walk a profile root and return records for every settings JSON."""
    root = Path(root)
    if not root.exists():
        return []
    out: list[ProfileRecord] = []
    for path in sorted(root.rglob("*.json")):
        if path.name in SKIP_NAMES:
            continue
        # Skip vendor index sidecars at profiles/*.json that only list printers
        if path.parent == root and path.suffix == ".json" and path.stem[0].isupper():
            # e.g. Creality.json index — still useful but not a settings blob
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or "name" not in data:
                continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            # index files without name — skip
            continue
        # vendor = first dir under root if nested
        try:
            rel = path.relative_to(root)
            vendor = vendor_hint or (rel.parts[0] if len(rel.parts) > 1 else root.name)
        except ValueError:
            vendor = vendor_hint or root.name
        inherits = data.get("inherits")
        if inherits is not None and not isinstance(inherits, str):
            inherits = str(inherits)
        out.append(
            ProfileRecord(
                name=name,
                path=str(path.resolve()),
                type=_guess_type(data, path),
                vendor=str(vendor),
                inherits=inherits,
                sha256=_sha256(path),
                source=source,
            )
        )
    return out


def harvest_all(
    *,
    orca_root: Path | None = None,
    bambu_root: Path | None = None,
    foundry_root: Path | None = None,
) -> dict[str, Any]:
    """Harvest Orca + optional Bambu extract + Foundry overrides."""
    orca_root = Path(orca_root or DEFAULT_ORCA_PROFILES)
    bambu_root = Path(bambu_root or DEFAULT_BAMBU_PROFILES)
    foundry_root = Path(
        foundry_root
        or os.environ.get("FOUNDRY_ORCA_PROFILES", str(Path.home() / "orcaslicer" / "profiles"))
    )

    records: list[ProfileRecord] = []
    records.extend(harvest_tree(orca_root, source="orca"))
    if bambu_root.exists():
        records.extend(harvest_tree(bambu_root, source="bambu", vendor_hint="BBL"))
    if foundry_root.exists():
        records.extend(harvest_tree(foundry_root, source="foundry", vendor_hint="Foundry"))

    by_name: dict[str, list[dict]] = {}
    vendors: set[str] = set()
    types: dict[str, int] = {}
    for rec in records:
        by_name.setdefault(rec.name, []).append(asdict(rec))
        vendors.add(rec.vendor)
        types[rec.type] = types.get(rec.type, 0) + 1

    return {
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "orca_root": str(orca_root),
        "bambu_root": str(bambu_root) if bambu_root.exists() else None,
        "foundry_root": str(foundry_root) if foundry_root.exists() else None,
        "count": len(records),
        "vendors": sorted(vendors),
        "types": types,
        # Prefer foundry > bambu > orca when multiple paths share a name
        "by_name": by_name,
        "records": [asdict(r) for r in records],
    }


def write_manifest(manifest: dict[str, Any], path: Path | None = None) -> Path:
    path = Path(path or DEFAULT_MANIFEST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def diff_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compare two harvests by name+sha256."""
    def index(m: dict[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for r in m.get("records") or []:
            out[r["name"]] = r.get("sha256") or ""
        return out

    a, b = index(old), index(new)
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(n for n in set(a) & set(b) if a[n] != b[n])
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
    }


def load_manifest(path: Path | None = None) -> dict[str, Any] | None:
    path = Path(path or DEFAULT_MANIFEST)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def resolve_from_harvest(name: str, *, prefer: Iterable[str] = ("foundry", "bambu", "orca")) -> Path | None:
    """Look up a profile path from the latest harvest manifest."""
    m = load_manifest()
    if not m:
        return None
    rows = (m.get("by_name") or {}).get(name) or []
    if not rows:
        return None
    pref = list(prefer)
    rows_sorted = sorted(
        rows,
        key=lambda r: pref.index(r["source"]) if r.get("source") in pref else 99,
    )
    p = Path(rows_sorted[0]["path"])
    return p if p.exists() else None
