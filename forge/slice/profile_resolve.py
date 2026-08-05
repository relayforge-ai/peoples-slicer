"""Flatten BambuStudio / Orca ``inherits`` chains into standalone JSON.

Stock profiles are not standalone. Example (A1 mini 0.4 nozzle):
  inherits: fdm_bbl_3dp_001_common  → printable_area would be 256×256 if not overridden
  leaf overrides: printable_area 180×180, default process/filament @BBL A1M

We deep-merge parent → child (child wins) so ``--load-settings`` gets a self-contained
file and fit checks see the *effective* bed, not the parent's 256 mm plate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Default locations (override with env for CI / alternate installs).
_PKG = Path(__file__).resolve().parent
_DEFAULT_BAMBU_CANDIDATES = [
    Path(os.environ.get("BAMBU_PROFILES", "")) if os.environ.get("BAMBU_PROFILES") else None,
    Path.home() / "print_work" / "multi_slicer" / "vendor_profiles" / "BBL",
    Path("/tmp/bambustudio-extract/squashfs-root/resources/profiles/BBL"),
]
_DEFAULT_BAMBU_CANDIDATES = [p for p in _DEFAULT_BAMBU_CANDIDATES if p is not None]


def _default_bambu_profiles() -> Path:
    env = os.environ.get("BAMBU_PROFILES")
    if env:
        return Path(env)
    for c in _DEFAULT_BAMBU_CANDIDATES:
        if c.exists():
            return c
    return _DEFAULT_BAMBU_CANDIDATES[0]


DEFAULT_BAMBU_PROFILES = _default_bambu_profiles()
DEFAULT_ORCA_PROFILES = Path(
    os.environ.get(
        "ORCA_PROFILES",
        str(Path.home() / "orcaslicer" / "squashfs-root" / "resources" / "profiles"),
    )
)
DEFAULT_FOUNDRY_ORCA = Path(
    os.environ.get("FOUNDRY_ORCA_PROFILES", str(Path.home() / "orcaslicer" / "profiles"))
)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge overlay onto base; nested dicts recurse, everything else is replaced."""
    out = dict(base)
    for k, v in overlay.items():
        if k == "inherits":
            continue  # flattened — drop the pointer
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ProfileIndex:
    """Name → path index over a profile tree (machine / process / filament JSON)."""

    def __init__(self, roots: list[Path]):
        self.by_name: dict[str, Path] = {}
        self.by_stem: dict[str, Path] = {}
        for root in roots:
            if not root or not Path(root).exists():
                continue
            root = Path(root)
            for path in root.rglob("*.json"):
                # Skip vendor index / cover sidecars that aren't settings.
                if path.name in {"cli_config.json", "blacklist.json"}:
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(data, dict):
                    continue
                name = data.get("name")
                if isinstance(name, str) and name:
                    self.by_name.setdefault(name, path)
                self.by_stem.setdefault(path.stem, path)

    def resolve_path(self, name: str) -> Path:
        if name in self.by_name:
            return self.by_name[name]
        if name in self.by_stem:
            return self.by_stem[name]
        # Exact filename
        for p in self.by_name.values():
            if p.name == name or p.name == f"{name}.json":
                return p
        raise FileNotFoundError(f"profile not found: {name!r}")

    def load_raw(self, name: str) -> tuple[Path, dict[str, Any]]:
        path = self.resolve_path(name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"profile is not an object: {path}")
        return path, data

    def inherits_chain(self, name: str) -> list[str]:
        """Return [leaf, parent, …, root] names."""
        chain: list[str] = []
        seen: set[str] = set()
        cur: str | None = name
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            try:
                _, data = self.load_raw(cur)
            except FileNotFoundError:
                break
            parent = data.get("inherits")
            cur = parent if isinstance(parent, str) and parent else None
        return chain

    def flatten(self, name: str) -> dict[str, Any]:
        """Deep-merge the inherits chain so the leaf's bed size wins over parents.

        REL-631: ``inherits_chain`` appends the *requested* name before it ever confirms
        that name resolves to a real file, so a completely empty index still returns a
        nonempty chain (``[name]``). A nonempty chain is therefore not proof that any real
        profile data exists. Raise unless at least one chain member actually loaded —
        otherwise a caller silently gets back ``{"_flattened_from": [name]}``, a hollow
        dict with no real settings, indistinguishable from a genuine profile at a glance
        (this is exactly how ``forge slice --dry-run`` reported ``ok: true`` against zero
        indexed profiles).
        """
        chain = self.inherits_chain(name)
        if not chain:
            raise FileNotFoundError(f"profile not found: {name!r}")
        # Root first, then children — so leaf overrides win.
        merged: dict[str, Any] = {}
        loaded_any = False
        for part in reversed(chain):
            try:
                _, data = self.load_raw(part)
            except FileNotFoundError:
                continue
            merged = _deep_merge(merged, data)
            loaded_any = True
        if not loaded_any:
            raise FileNotFoundError(
                f"profile not found: {name!r} — 0 profiles indexed from the configured "
                f"profile root(s). Point BAMBU_PROFILES (or ORCA_PROFILES) at an extracted "
                f"slicer AppImage's resources/profiles directory, e.g. run "
                f"`<AppImage> --appimage-extract` and set the env var to "
                f"squashfs-root/resources/profiles[/BBL]."
            )
        merged.pop("inherits", None)
        merged["_flattened_from"] = chain
        return merged


def bambu_index() -> ProfileIndex:
    return ProfileIndex([DEFAULT_BAMBU_PROFILES])


def orca_index() -> ProfileIndex:
    # Foundry overrides (Ender Klipper) first so name lookups prefer studio profiles.
    return ProfileIndex([DEFAULT_FOUNDRY_ORCA, DEFAULT_ORCA_PROFILES])


def write_flattened(index: ProfileIndex, name: str, dest: Path) -> Path:
    """Write a flattened profile JSON to dest and return the path."""
    data = index.flatten(name)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dest


def printable_xy_mm(flattened: dict[str, Any]) -> float | None:
    """Max XY extent from printable_area polygon (e.g. 180 for A1 mini)."""
    area = flattened.get("printable_area")
    if not area or not isinstance(area, list):
        return None
    xs: list[float] = []
    ys: list[float] = []
    for pt in area:
        if not isinstance(pt, str) or "x" not in pt:
            continue
        a, b = pt.split("x", 1)
        try:
            xs.append(float(a))
            ys.append(float(b))
        except ValueError:
            continue
    if not xs or not ys:
        return None
    return max(max(xs) - min(xs), max(ys) - min(ys))
