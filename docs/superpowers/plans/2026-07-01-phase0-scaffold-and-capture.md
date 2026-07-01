# Telchar's Forge — Phase 0: Scaffold + Capture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the public `peoples-slicer` repo as an installable Python package ("Telchar's Forge", CLI `forge`) with a green test harness, and freeze real hardware truth into `fixtures/` — so the 3-week hardware-less away-sprint can build and test the engine against recorded reality.

**Architecture:** Part A (agent, hardware-less, TDD) scaffolds the package, CLI banner, and fixture-loading harness, and inventories exactly which functions to extract from the proven private code. Part B (Ryan, on hardware this week) is a capture runbook that saves per-printer API/gcode truth into `fixtures/`. Nothing here touches a live printer from code; captures are deliberate, saved artifacts.

**Tech Stack:** Python ≥3.11, `argparse` (zero-dep CLI), `pytest` (dev). Later phases add `watchdog` (file-watch) and `zeroconf` (discovery) — NOT in Phase 0.

## Global Constraints

- **Python ≥ 3.11.** Engine must run on **Windows 11** (ganymede) and Linux. Verify ganymede's Python version in Task 4.
- **Names:** product brand **Telchar's Forge**; umbrella **The People's Slicer**; package + CLI = `forge` (fallback `telforge` only if the binary name collides on a user's machine).
- **Public repo is MIT and secretless.** NEVER commit LAN IPs, printer access codes, `~/.relayforge_secrets`, Mongo URIs, or Tailscale keys. Captured fixtures must be scrubbed of secrets (redact serial numbers / check codes → `REDACTED`).
- **Brand copy (verbatim):** any CLI banner / README hero / viewer footer MUST contain `telchar.relayforge.tools`. Tagline, verbatim: `you slice, it does the rest.`
- **Cross-platform:** file-watching uses `watchdog`, never raw inotify; no `systemd` assumptions in the engine. OS-specific bits live in the private deployment, not here.
- **No hot-path inference:** the engine is deterministic; any LLM call is behind a pluggable hook and is never required for a print to proceed.
- TDD, DRY, YAGNI, frequent commits.

---

## File Structure (Phase 0 creates)

- `pyproject.toml` — package metadata, `forge` entry point, pytest config.
- `forge/__init__.py` — `__version__`, brand constants.
- `forge/cli.py` — argparse CLI, banner, stubbed subcommands (`discover|review|send|status|watch`).
- `forge/fixtures.py` — fixture loader + schema (the away-sprint's test harness).
- `tests/test_cli.py`, `tests/test_fixtures.py`.
- `fixtures/README.md` + `fixtures/{bambu_a2l,ad5x,ender}/…` — captured hardware truth.
- `docs/EXTRACTION_MAP.md` — exact functions to lift from the private code into Plan 1.
- `.gitignore`.

---

# PART A — Scaffold (agent, hardware-less, TDD)

### Task 1: Python package + branded CLI

**Files:**
- Create: `pyproject.toml`
- Create: `forge/__init__.py`
- Create: `forge/cli.py`
- Create: `.gitignore`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `forge.__version__: str`; `forge.BRAND` (dict with keys `product`, `umbrella`, `tagline`, `home_url`); `forge.cli.build_parser() -> argparse.ArgumentParser`; `forge.cli.banner() -> str`; `forge.cli.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import forge
from forge import cli


def test_version_is_semver():
    parts = forge.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_banner_carries_the_brand_and_funnel():
    b = cli.banner()
    assert "Telchar's Forge" in b
    assert "The People's Slicer" in b
    assert "you slice, it does the rest." in b        # verbatim tagline
    assert "telchar.relayforge.tools" in b            # the funnel, always


def test_help_lists_the_five_subcommands(capsys):
    rc = cli.main(["--help"])
    out = capsys.readouterr().out
    for sub in ("discover", "review", "send", "status", "watch"):
        assert sub in out
    assert rc == 0


def test_bare_invocation_prints_banner_and_succeeds(capsys):
    rc = cli.main([])
    out = capsys.readouterr().out
    assert "telchar.relayforge.tools" in out
    assert rc == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forge'`.

- [ ] **Step 3: Write the package**

```python
# forge/__init__.py
"""Telchar's Forge — the harness that runs everything after the slice.

Part of The People's Slicer (MIT). You slice in Orca; the Forge discovers your
printers, reviews the finicky parameters, sends headless with zero parameter
loss, and hands the job to an AI operator that runs it safely.
"""
__version__ = "0.1.0"

BRAND = {
    "product": "Telchar's Forge",
    "umbrella": "The People's Slicer",
    "tagline": "you slice, it does the rest.",
    "home_url": "telchar.relayforge.tools",
}
```

```python
# forge/cli.py
"""The `forge` command — argparse, zero third-party deps (mom-simple, Windows-safe)."""
from __future__ import annotations

import argparse

from . import BRAND, __version__

SUBCOMMANDS = ("discover", "review", "send", "status", "watch")


def banner() -> str:
    return (
        f"{BRAND['product']} v{__version__} — {BRAND['tagline']}\n"
        f"Part of {BRAND['umbrella']} · made in the Telchar studio "
        f"→ {BRAND['home_url']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge",
        description=banner(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"forge {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="{" + ",".join(SUBCOMMANDS) + "}")
    for name, help_text in (
        ("discover", "find and connect printers on the LAN (enter a code once)"),
        ("review", "audit a sliced file's finicky parameters for a printer/material"),
        ("send", "send a sliced file to a printer, headless, zero parameter loss"),
        ("status", "show what is queued and printing"),
        ("watch", "watch a drop folder and route jobs automatically"),
    ):
        sub.add_parser(name, help=help_text)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print(banner())
        print("\nRun `forge --help` for commands.")
        return 0
    # Subcommands are stubbed in Phase 0; the engine lands in Plans 1–2.
    print(f"`forge {args.command}` is not implemented yet — see docs/superpowers/plans/.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "telchars-forge"
version = "0.1.0"
description = "Telchar's Forge — the harness that runs everything after the slice. Part of The People's Slicer."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "RelayForge / Ryan Anderson" }]
keywords = ["3d-printing", "slicer", "orcaslicer", "bambu", "flashforge", "klipper", "cli"]
dependencies = []

[project.urls]
Homepage = "https://telchar.relayforge.tools"

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
forge = "forge.cli:main"

[tool.setuptools.packages.find]
include = ["forge*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```gitignore
# .gitignore
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
build/
dist/
.venv/
# never leak local deployment secrets into the public repo
*.secrets
.relayforge_secrets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Verify the installed console script works**

Run: `pip install -e . && forge --version && forge`
Expected: prints `forge 0.1.0`, then the banner with `telchar.relayforge.tools`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml forge/ tests/test_cli.py .gitignore
git commit -m "feat: scaffold Telchar's Forge package + branded forge CLI"
```

---

### Task 2: Fixture-loading harness

The away-sprint tests every adapter against captured payloads instead of a live printer. This task builds the loader and locks the on-disk schema so Part B captures into the right shape.

**Files:**
- Create: `forge/fixtures.py`
- Create: `fixtures/README.md`
- Test: `tests/test_fixtures.py`

**Interfaces:**
- Produces: `forge.fixtures.FIXTURES_ROOT: Path`; `forge.fixtures.load(printer: str, name: str) -> dict` (reads `fixtures/<printer>/<name>.json`); `forge.fixtures.load_text(printer: str, name: str) -> str` (reads any non-JSON artifact, e.g. `.gcode`); `forge.fixtures.available(printer: str) -> list[str]`. Raises `FixtureNotFound(printer, name)` with a message pointing at the capture runbook.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixtures.py
import json

import pytest

from forge import fixtures


def test_missing_fixture_points_at_the_runbook():
    with pytest.raises(fixtures.FixtureNotFound) as exc:
        fixtures.load("ad5x", "does_not_exist")
    assert "capture" in str(exc.value).lower()


def test_round_trip_json_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "FIXTURES_ROOT", tmp_path)
    (tmp_path / "ad5x").mkdir()
    payload = {"useMatlStation": True, "materialMappings": [{"toolId": 0, "slotId": 1}]}
    (tmp_path / "ad5x" / "print_gcode_request.json").write_text(json.dumps(payload))
    assert fixtures.load("ad5x", "print_gcode_request") == payload
    assert "print_gcode_request" in fixtures.available("ad5x")


def test_load_text_reads_gcode(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "FIXTURES_ROOT", tmp_path)
    (tmp_path / "bambu_a2l").mkdir()
    (tmp_path / "bambu_a2l" / "golden.gcode").write_text("; header\nG28\n")
    assert "G28" in fixtures.load_text("bambu_a2l", "golden.gcode")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fixtures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forge.fixtures'`.

- [ ] **Step 3: Write the loader**

```python
# forge/fixtures.py
"""Load captured hardware truth so tests never need a live printer.

Layout:  fixtures/<printer>/<name>.json   (parsed)  |  <name>.<ext>  (raw text)
Printers: bambu_a2l | ad5x | ender
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


class FixtureNotFound(FileNotFoundError):
    def __init__(self, printer: str, name: str):
        super().__init__(
            f"No fixture {printer!r}/{name!r}. Capture it on hardware first — "
            f"see docs/superpowers/plans/2026-07-01-phase0-scaffold-and-capture.md (Part B)."
        )


def _dir(printer: str) -> Path:
    return FIXTURES_ROOT / printer


def load(printer: str, name: str) -> dict:
    path = _dir(printer) / f"{name}.json"
    if not path.exists():
        raise FixtureNotFound(printer, name)
    return json.loads(path.read_text())


def load_text(printer: str, name: str) -> str:
    path = _dir(printer) / name
    if not path.exists():
        raise FixtureNotFound(printer, name)
    return path.read_text()


def available(printer: str) -> list[str]:
    d = _dir(printer)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))
```

```markdown
<!-- fixtures/README.md -->
# Captured hardware truth

Real printer/API captures so the engine is testable with NO printer attached.
**Scrub secrets** before committing: replace serial numbers and check codes with `REDACTED`.

```
fixtures/
  bambu_a2l/   golden.gcode · mqtt_start.json · ftps_upload_trace.txt · wifi_cancel_case.txt
  ad5x/        golden_multicolor.gcode.3mf · print_gcode_request.json · ifs_slot_state.json
               material_mappings.json · mono_without_ifs_case.txt
  ender/       golden.gcode · moonraker_upload.json · print_start.json · mcu_drop_400.txt
```
See the Print Flow Runbook (Notion) for what each capture means.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fixtures.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add forge/fixtures.py fixtures/README.md tests/test_fixtures.py
git commit -m "feat: fixture-loading harness (test adapters without a printer)"
```

---

### Task 3: Extraction inventory (`docs/EXTRACTION_MAP.md`)

Plan 1 lifts the proven private code into the public engine. This task catalogues *exactly* what to lift, so Plan 1's tasks reference real functions instead of guessing. The executing agent READS the source and records signatures — it does not copy secrets.

**Files:**
- Create: `docs/EXTRACTION_MAP.md`
- Test: `tests/test_extraction_map.py`

- [ ] **Step 1: Write the failing test** (structural — the map must cover every engine module + name a secret-scrub rule)

```python
# tests/test_extraction_map.py
from pathlib import Path

MAP = Path("docs/EXTRACTION_MAP.md")


def test_map_exists_and_covers_every_engine_module():
    text = MAP.read_text()
    for module in ("classifier", "reader", "jobqueue", "dispatcher",
                   "adapters/ad5x", "adapters/bambu", "adapters/klipper"):
        assert module in text, f"EXTRACTION_MAP missing {module}"


def test_map_states_the_secret_scrub_rule():
    text = MAP.read_text().lower()
    assert "secret" in text and "redact" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_extraction_map.py -v`
Expected: FAIL — `FileNotFoundError` / assertion (file absent).

- [ ] **Step 3: Produce the map** — read the sources and fill this table. Sources to open:
  `~/print-router/print_router/{classifier,reader,jobqueue,dispatcher,drive_inbox}.py` and `adapters/`,
  `~/Desktop/3d_prints_tests/ad5x_tools/{ad5x,ad5x_mc,ad5x_send,ad5x_start,ad5x_print}.py`,
  `~/print_work/send_bambu.py`, `~/makerlobster-catalog/print_flow.py`.

```markdown
<!-- docs/EXTRACTION_MAP.md -->
# Extraction map — private proven code → public Forge engine

For each public module: the source file(s), the exact functions/classes to lift, the
public signature they become, and what must be genericised (secrets/paths → config).

**Secret-scrub rule (MANDATORY):** nothing lifted may carry LAN IPs, access codes,
serials, check codes, Mongo URIs, or Drive paths. Those become constructor/config
parameters. Redact any example values to `REDACTED`.

| Public module | Source | Lift | Becomes (signature) | Genericise |
|---------------|--------|------|---------------------|------------|
| `forge/classifier.py` | `print-router/.../classifier.py` | routing decision fn | `classify(header: str) -> Classification` | — |
| `forge/reader.py` | `print-router/.../reader.py` | head+tail read | `read_gcode_meta(path) -> str` | — |
| `forge/jobqueue.py` | `print-router/.../jobqueue.py` | FIFO + dedupe + persist | `JobQueue(state_dir: Path)` | state dir → param |
| `forge/dispatcher.py` | `print-router/.../dispatcher.py` | idle→send/busy→queue + event seam | `Dispatcher(adapters, queue, sink)` | event sink → pluggable |
| `forge/adapters/base.py` | (new, from the adapter interface) | the contract | `status()/send()/watch()/stop()` | — |
| `forge/adapters/ad5x.py` | `ad5x_tools/ad5x*.py` incl. `ad5x_mc.py` | 8899 send + 8898 status + **IFS auto-map** | `AD5XAdapter(host, ...)` | host/serial/checkcode → params |
| `forge/adapters/bambu.py` | `send_bambu.py` | FTPS upload + MQTT start + AMS map | `BambuAdapter(host, access_code, serial)` | creds → params |
| `forge/adapters/klipper.py` | Moonraker calls in `print-router` | upload + start + FIRMWARE_RESTART | `KlipperAdapter(moonraker_url)` | url → param |

**Notes column** (fill while reading): quirks, retry logic, single-client politeness, the
exact `materialMappings` build in `ad5x_mc.py` (the keystone).
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_extraction_map.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Full suite green + commit**

```bash
python -m pytest -q      # all Phase-0 Part-A tests green
git add docs/EXTRACTION_MAP.md tests/test_extraction_map.py
git commit -m "docs: extraction map (private proven code -> public Forge engine)"
```

---

# PART B — Capture (Ryan, on hardware, this week — a runbook, not TDD)

> These are deliberate saves of real hardware truth into `fixtures/`. Do them while the
> A2L / AD5X / Ender are in front of you (before vacation). Scrub serials + check codes to
> `REDACTED` before `git add`. Each saved file makes one away-sprint test possible.

### Task 4: Capture per-printer fixtures + ganymede facts

- [ ] **ganymede facts** → append to the spec's Phase-0 list: Python version (`python --version`),
      whether Mongo is installed/running. (Online + on Tailscale as of 2026-07-01 ✓.)
- [ ] **Bambu A2L X/Y** build dimensions (height 325 mm already recorded) → note in the spec.
- [ ] **Golden gcode per printer** (slice a known model in Orca, export) →
      `fixtures/bambu_a2l/golden.gcode`, `fixtures/ad5x/golden_multicolor.gcode.3mf`,
      `fixtures/ender/golden.gcode`. These are the zero-parameter-loss diff baseline.
- [ ] **AD5X keystone** — capture from a real multicolor start:
      `print_gcode_request.json` (the `/printGcode` body with `useMatlStation` + `materialMappings`),
      `ifs_slot_state.json` (`/detail` → `matlStationInfo.slotInfos`),
      and a `mono_without_ifs_case.txt` note of the failing mono start. → `fixtures/ad5x/`.
- [ ] **Bambu** — `mqtt_start.json` (the MQTT print-start payload), `ftps_upload_trace.txt`,
      and a `wifi_cancel_case.txt` capture of the silent-cancel. → `fixtures/bambu_a2l/`.
- [ ] **Ender/Klipper** — `moonraker_upload.json`, `print_start.json`, and `mcu_drop_400.txt`
      (the "Lost communication with MCU" 400 + the firmware_restart recovery). → `fixtures/ender/`.
- [ ] **Commit** each printer's captures:
      `git add fixtures/<printer>/ && git commit -m "fixtures: capture <printer> hardware truth (scrubbed)"`.

**Done when:** `forge.fixtures.available("bambu_a2l" | "ad5x" | "ender")` each return the captured
names, and the golden gcode + AD5X keystone JSON are present and secret-scrubbed. The away-sprint
(Plans 1–2) can now build every adapter against recorded reality.

---

## Self-Review

- **Spec coverage (Phase 0 slice):** repo scaffold ✓ (T1) · fixture harness ✓ (T2) · extraction
  inventory for the public/private split ✓ (T3) · Phase-0 capture list incl. ganymede facts + A2L
  X/Y + the 3 failure-case regressions ✓ (T4). Build of adapters/discover/review/viewer/docs =
  deferred to Plans 1–3 by design.
- **Placeholders:** none — all scaffold/harness code is complete; T3/T4 are read-and-record /
  capture tasks whose outputs are schema-checked or file-presence-checked.
- **Type consistency:** `fixtures.load/load_text/available/FixtureNotFound`, `cli.banner/build_parser/main`,
  `BRAND`/`__version__` are used identically in tests and impl. `forge` package name matches
  `pyproject` entry point `forge = "forge.cli:main"`.
