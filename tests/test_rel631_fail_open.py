"""REL-631 — the dry-run fail-open: a missing profile must fail loudly, not report ok=True.

Found via a cold-start test (agent, no runbook): ``forge slice --dry-run`` returned
``{"ok": true, ...}`` with plausible-looking bounds while ``bambu_index().by_name`` was
empty. The bounds come straight from the STL's own geometry and have nothing to do with
whether a real BambuStudio/Orca profile was ever found. ``ProfileIndex.flatten()`` was
swallowing ``FileNotFoundError`` per inherits-chain member and returning
``{"_flattened_from": [name]}`` — a dict with zero real settings — instead of raising.
The one guard meant to catch a profile problem (bed-size mismatch) is gated on
``printable_xy_mm(...) is not None``, which is ``False`` for a missing profile, so it never
fired on the case it exists to catch.
"""
from __future__ import annotations

import pytest

from forge.slice import backends
from forge.slice.api import SliceError, slice_for
from forge.slice.profile_resolve import ProfileIndex

_ASCII_CUBE = (
    "solid c\n facet normal 0 0 1\n  outer loop\n"
    "   vertex 0 0 0\n   vertex 10 0 0\n   vertex 10 10 0\n"
    "  endloop\n endfacet\n"
    " facet normal 0 0 1\n  outer loop\n"
    "   vertex 0 0 0\n   vertex 10 10 0\n   vertex 0 10 0\n"
    "  endloop\n endfacet\nendsolid c\n"
)


def test_flatten_raises_on_completely_empty_index():
    """An index over a nonexistent root has zero profiles. Asking it to flatten anything
    must fail loudly, not return a hollow ``{"_flattened_from": [...]}`` placeholder."""
    idx = ProfileIndex(["/nonexistent/profile/root/for/rel631/test"])
    assert len(idx.by_name) == 0
    with pytest.raises(FileNotFoundError):
        idx.flatten("Bambu Lab A1 mini 0.4 nozzle")


def test_inherits_chain_raises_on_missing_leaf():
    """``inherits_chain`` must not append the requested name and return a hollow
    1-element chain when the leaf does not resolve — that was the REL-631 root cause
    (flatten then skipped every load and returned ``{_flattened_from: [name]}``)."""
    idx = ProfileIndex(["/nonexistent/profile/root/for/rel631/test"])
    with pytest.raises(FileNotFoundError) as ei:
        idx.inherits_chain("Bambu Lab A1 mini 0.4 nozzle")
    assert "profile not found" in str(ei.value).lower()
    with pytest.raises(FileNotFoundError):
        idx.flatten("Bambu Lab A1 mini 0.4 nozzle")


def test_flatten_error_message_is_actionable():
    """The failure should tell the caller what's missing and how to fix it — not just
    a bare 'not found'."""
    idx = ProfileIndex(["/nonexistent/profile/root/for/rel631/test"])
    with pytest.raises(FileNotFoundError) as exc_info:
        idx.flatten("Bambu Lab A1 mini 0.4 nozzle")
    msg = str(exc_info.value).lower()
    assert "profile" in msg
    # Should point at the fix, not just the symptom.
    assert "bambu_profiles" in msg or "orca_profiles" in msg or "appimage" in msg


def test_flatten_still_works_on_a_real_profile(tmp_path):
    """Sanity check the fix doesn't break the legitimate case: a real, self-contained
    profile (no ``inherits``) must still flatten cleanly."""
    real = tmp_path / "leaf.json"
    real.write_text('{"name": "Test Leaf", "printable_area": ["0x0", "180x0", "180x180", "0x180"]}')
    idx = ProfileIndex([tmp_path])
    flat = idx.flatten("Test Leaf")
    assert flat["printable_area"] == ["0x0", "180x0", "180x180", "0x180"]


# --- End-to-end: slice_for(..., dry_run=True) must not report ok=True on an empty index ---
# This is the actual reported bug's exact repro shape: no BAMBU_PROFILES configured, a
# completely empty ProfileIndex, `forge slice --dry-run` returning a clean success.


@pytest.mark.parametrize("printer_key", ["a1mini", "a2l"])
def test_dry_run_raises_when_bambu_profiles_missing(tmp_path, monkeypatch, printer_key):
    """The original bug reproduced literally: with zero Bambu profiles indexed,
    `slice_for(..., dry_run=True)` must raise, not return `SliceResult(ok=True, ...)`.
    Parametrized over two Bambu-backend printers — the pre-fix guard only ever checked
    `spec.key == "a1mini"`, so a2l was silently uncovered even when the a1mini case was
    caught by other means. The fix must not be printer-specific."""
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([]))
    stl = tmp_path / "cube.stl"
    stl.write_text(_ASCII_CUBE)
    with pytest.raises((SliceError, FileNotFoundError)):
        slice_for(stl, printer_key, dry_run=True)


def test_dry_run_raises_when_orca_profiles_missing(tmp_path, monkeypatch):
    """Same bug, orca backend (ad5x/ender). The orca branch in `build_backend_cmd` catches
    a missing vendor profile and substitutes a Foundry fallback path — but previously did so
    unconditionally, even when that fallback path doesn't exist either. Must still raise."""
    monkeypatch.setattr(backends, "orca_index", lambda: ProfileIndex([]))
    monkeypatch.setattr(backends, "DEFAULT_FOUNDRY_ORCA", tmp_path / "nonexistent_foundry_dir")
    stl = tmp_path / "cube.stl"
    stl.write_text(_ASCII_CUBE)
    with pytest.raises((SliceError, FileNotFoundError)):
        slice_for(stl, "ad5x", dry_run=True)
