"""Flatten BambuStudio / Orca ``inherits`` chains into standalone JSON.

Stock profiles are not standalone. Example (A1 mini 0.4 nozzle):
  inherits: fdm_bbl_3dp_001_common  → printable_area would be 256×256 if not overridden
  leaf overrides: printable_area 180×180, default process/filament @BBL A1M

We deep-merge parent → child (child wins) so ``--load-settings`` gets a self-contained
file and fit checks see the *effective* bed, not the parent's 256 mm plate.

REL-631 / zero-parameter-loss: missing chain members and empty merges raise.
Never report success from a hollow ``{"_flattened_from": [name]}`` profile.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .profile_validate import ensure_process_line_widths, validate_flattened_profile

# Persistent locations only. `/tmp` extracts die on reboot (REL-602 #3 —
# A1 mini symlink into /tmp/bambustudio-extract, every slice returned -5).
_PKG = Path(__file__).resolve().parent
_EPHEMERAL_ROOTS = ("/tmp", "/var/tmp")


def _is_ephemeral(path: Path) -> bool:
    """True for /tmp and /var/tmp trees — they do not survive a reboot."""
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = path.expanduser()
    text = str(resolved)
    return any(text == root or text.startswith(root + "/") for root in _EPHEMERAL_ROOTS)


def _profile_tree_ok(path: Path) -> bool:
    if _is_ephemeral(path):
        return False
    if not path.exists() or not path.is_dir():
        return False
    try:
        return next(path.rglob("*.json"), None) is not None
    except OSError:
        return False


def _persistent_bambu_candidates() -> list[Path]:
    """Load-bearing BBL roots. Never includes /tmp."""
    env = os.environ.get("BAMBU_PROFILES")
    out: list[Path] = []
    if env:
        out.append(Path(env).expanduser())
    out.extend(
        [
            _PKG / "vendor_profiles" / "BBL",
            Path.home() / ".forge" / "vendor_profiles" / "BBL",
            Path.home() / "print_work" / "multi_slicer" / "vendor_profiles" / "BBL",
        ]
    )
    return out


def _default_bambu_profiles(*, require: bool = False) -> Path:
    """Resolve a persistent BBL tree.

    When ``require`` is True (slice / flatten), a missing or `/tmp` tree raises
    instead of returning a path we just proved absent — that silent-wrong path
    is how every A1 mini slice broke after the Dawes reboot.
    """
    candidates = _persistent_bambu_candidates()
    env = os.environ.get("BAMBU_PROFILES")
    if env:
        chosen = Path(env).expanduser()
        if _is_ephemeral(chosen):
            raise FileNotFoundError(
                f"BAMBU_PROFILES={chosen} is under /tmp and will vanish on reboot "
                f"(REL-602). Copy the tree to ~/.forge/vendor_profiles/BBL and "
                f"point BAMBU_PROFILES there."
            )
        if require and not _profile_tree_ok(chosen):
            raise FileNotFoundError(
                f"BAMBU_PROFILES={chosen} is missing or has no JSON profiles. "
                f"Extract the BambuStudio AppImage to a persistent path "
                f"(~/.forge/vendor_profiles/BBL), not /tmp."
            )
        return chosen
    for c in candidates:
        if _profile_tree_ok(c):
            return c
    fallback = Path.home() / ".forge" / "vendor_profiles" / "BBL"
    if require:
        raise FileNotFoundError(
            f"no persistent Bambu vendor profiles found. Looked at: "
            f"{[str(c) for c in candidates]}. Extract BambuStudio with "
            f"`AppImage --appimage-extract 'resources/profiles/BBL'` and copy "
            f"that tree to {fallback} (never /tmp)."
        )
    return fallback


def _default_orca_profiles(*, require: bool = False) -> Path:
    env = os.environ.get("ORCA_PROFILES")
    chosen = Path(
        env
        or (
            Path.home()
            / "orcaslicer"
            / "squashfs-root"
            / "resources"
            / "profiles"
        )
    ).expanduser()
    if _is_ephemeral(chosen):
        raise FileNotFoundError(
            f"ORCA_PROFILES={chosen} is under /tmp and will vanish on reboot. "
            f"Use a persistent extract (e.g. ~/orcaslicer/squashfs-root/resources/profiles)."
        )
    if require and env and not _profile_tree_ok(chosen):
        raise FileNotFoundError(
            f"ORCA_PROFILES={chosen} is missing or has no JSON profiles."
        )
    return chosen


DEFAULT_BAMBU_PROFILES = _default_bambu_profiles()
DEFAULT_ORCA_PROFILES = _default_orca_profiles()
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
        """Return [leaf, parent, …, root] names.

        Fail-closed: a missing leaf or a broken parent link raises. Silently
        stopping mid-chain used to leave dry-run / slice looking "ok" with an
        empty flattened profile (zero parameter loss violated).
        """
        chain: list[str] = []
        seen: set[str] = set()
        cur: str | None = name
        while cur and cur not in seen:
            seen.add(cur)
            try:
                _, data = self.load_raw(cur)
            except FileNotFoundError as e:
                if not chain:
                    raise FileNotFoundError(
                        f"profile not found: {cur!r} (requested leaf {name!r}). "
                        f"{len(self.by_name)} profiles indexed from the configured root(s). "
                        f"Point BAMBU_PROFILES (or ORCA_PROFILES) at an extracted slicer "
                        f"AppImage's resources/profiles directory, e.g. run "
                        f"`<AppImage> --appimage-extract` and set the env var to "
                        f"squashfs-root/resources/profiles[/BBL]."
                    ) from e
                raise FileNotFoundError(
                    f"broken inherits chain for {name!r}: missing parent {cur!r} "
                    f"(resolved so far: {chain})"
                ) from e
            chain.append(cur)
            parent = data.get("inherits")
            cur = parent if isinstance(parent, str) and parent else None
        return chain

    def flatten(self, name: str) -> dict[str, Any]:
        """Deep-merge the inherits chain so the leaf's bed size wins over parents.

        REL-631: never swallow missing members. A hollow
        ``{"_flattened_from": [name]}`` must not look like success to dry-run.
        """
        chain = self.inherits_chain(name)
        if not chain:
            raise FileNotFoundError(f"profile not found: {name!r}")
        # Root first, then children — so leaf overrides win.
        merged: dict[str, Any] = {}
        for part in reversed(chain):
            _, data = self.load_raw(part)
            merged = _deep_merge(merged, data)
        merged.pop("inherits", None)
        merged["_flattened_from"] = chain
        identity = (
            merged.get("name")
            or merged.get("printer_model")
            or merged.get("printer_settings_id")
            or merged.get("print_settings_id")
            or merged.get("filament_settings_id")
        )
        if not identity and not merged.get("printable_area") and not merged.get("nozzle_diameter"):
            raise FileNotFoundError(
                f"profile flatten for {name!r} produced an empty settings object "
                f"(chain={chain}) — refusing to treat as success. Point BAMBU_PROFILES "
                f"(or ORCA_PROFILES) at an extracted slicer AppImage's resources/profiles."
            )
        return merged


def bambu_index() -> ProfileIndex:
    # Resolve live so tests / env changes are not stuck with import-time /tmp.
    return ProfileIndex([_default_bambu_profiles(require=True)])


def orca_index() -> ProfileIndex:
    # Foundry overrides first so name lookups prefer studio profiles.
    foundry = Path(
        os.environ.get("FOUNDRY_ORCA_PROFILES", str(DEFAULT_FOUNDRY_ORCA))
    ).expanduser()
    return ProfileIndex([foundry, _default_orca_profiles()])


def write_flattened(
    index: ProfileIndex,
    name: str,
    dest: Path,
    *,
    role: str | None = None,
) -> Path:
    """Write a flattened profile JSON to dest and return the path.

    When ``role`` is set (machine / process / filament), validate identity and
    required keys *before* the C++ slicer sees a hollow file.
    """
    data = index.flatten(name)
    if role == "process":
        data = ensure_process_line_widths(data)
    if role in {"machine", "process", "filament"}:
        validate_flattened_profile(data, role=role, requested=name)
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
