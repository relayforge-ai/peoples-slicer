# Telchar's Forge — Plan 1: the engine (extract proven core → adapters → guardian)

> Execute task-by-task (TDD). Phase 1 is buildable NOW, hardware-less. Phases 2–3 are the away-sprint (need Sunday's captured fixtures + hardware validation).

**Goal:** Give the public `forge/` package a real engine: the deterministic **core** (classify → queue → dispatch, with a pluggable event sink), then per-printer **adapters** behind one contract, then the **Amos guardian**. When Phase 1 lands, the public repo has a working, tested core — the bar for flipping the repo public.

**Architecture:** Lift the *already-proven, already-secretless* router core from private `~/print-router` into public `forge/` (nearly copy — these modules are pure logic; secrets live only in adapters). The dispatcher talks to printers through one `Adapter` Protocol (`status()`/`send()`), so adapters drop in later. Events flow to a pluggable `store` (default `JsonlStore` → `jobs.jsonl`; the private Telchar deployment swaps in Mongo).

**Tech stack:** Python ≥3.11, stdlib only (Phase 1). Tests via `pytest`.

## Global constraints
- **Secretless public repo** — the core carries NO LAN IPs / credentials (verified: classifier/reader/jobqueue/dispatcher/base are pure). Adapter secrets (Phase 2) become constructor params.
- **No hot-path inference**; deterministic core. **Adapter Protocol = `status() -> 'idle'|'printing'|'offline'` + `send(gcode_path, start) -> str`** (verbatim from the proven `adapters/base.py`).
- Keep relative imports inside `forge/` (`.jobqueue`, `.reader`). Ported tests change `print_router` → `forge`.
- Real signatures (from the extraction map, verified): `JobQueue(state_path)`, `Dispatcher(adapters, queue, store=None)`.

---

# PHASE 1 — extract the deterministic core (BUILD NOW, hardware-less)

**Source (private, secretless, verified pure logic):** `~/print-router/print_router/{classifier,reader,jobqueue,dispatcher}.py` + `adapters/base.py`; tests `~/print-router/tests/test_{classifier,reader,jobqueue,dispatcher}.py`.

### Task 1: classifier + reader
- [ ] Copy `~/print-router/print_router/classifier.py` → `forge/classifier.py` **unchanged** (pure; `classify(header) -> JobInfo`).
- [ ] Copy `reader.py` → `forge/reader.py` unchanged (keeps `from .classifier import ...`).
- [ ] Port `test_classifier.py`, `test_reader.py` → `tests/test_classifier.py`, `tests/test_reader.py`, changing any `print_router` import prefix → `forge`.
- [ ] Run `python3 -m pytest tests/test_classifier.py tests/test_reader.py -v` → PASS.
- [ ] Commit `feat(engine): extract classifier + reader (pure gcode-header routing)`.

### Task 2: jobqueue
- [ ] Copy `jobqueue.py` → `forge/jobqueue.py` unchanged (`JobQueue(state_path)`; atomic, crash-recoverable FIFO + dedupe).
- [ ] Port `test_jobqueue.py` → `tests/test_jobqueue.py` (`print_router` → `forge`).
- [ ] Run those tests → PASS.
- [ ] Commit `feat(engine): extract crash-recoverable job queue`.

### Task 3: dispatcher + Adapter Protocol + pluggable store
- [ ] Copy `adapters/base.py` → `forge/adapters/base.py` (the `Adapter` Protocol) and add `forge/adapters/__init__.py`.
- [ ] Copy `dispatcher.py` → `forge/dispatcher.py` unchanged (imports `.jobqueue`, `.reader`; `store` seam intact).
- [ ] **Add `forge/store.py`** — the default public event sink (the private deploy swaps Mongo in behind this same interface):
```python
"""Event sinks for the dispatcher. Public default = append-only jobs.jsonl."""
import json
from pathlib import Path

class JsonlStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: dict) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

class NullStore:
    def record(self, event: dict) -> None:  # for tests / dry-run
        pass
```
- [ ] **Add `tests/test_store.py`**:
```python
import json
from forge.store import JsonlStore, NullStore

def test_jsonl_store_appends(tmp_path):
    s = JsonlStore(str(tmp_path / "jobs.jsonl"))
    s.record({"state": "printing", "printer": "bambu"})
    s.record({"state": "queued", "printer": "ender"})
    lines = (tmp_path / "jobs.jsonl").read_text().splitlines()
    assert [json.loads(x)["state"] for x in lines] == ["printing", "queued"]

def test_null_store_is_noop():
    NullStore().record({"anything": 1})  # must not raise
```
- [ ] Port `test_dispatcher.py` → `tests/test_dispatcher.py` (`print_router` → `forge`; it uses fake adapters + a fake/None store — keep that).
- [ ] Run the full core suite `python3 -m pytest tests/ -v` → all PASS (classifier + reader + jobqueue + store + dispatcher), **no hardware**.
- [ ] Commit `feat(engine): extract dispatcher + Adapter protocol + pluggable JsonlStore`.

**Phase 1 done when:** `forge/` has classifier/reader/jobqueue/dispatcher/store/adapters.base with the ported core tests green — a working, secretless, hardware-less engine core.

---

# PHASE 2 — adapters (AWAY-SPRINT; needs Sunday fixtures)

One file per printer implementing the `Adapter` Protocol (`status()`/`send()`); secrets → constructor params. Tested against `fixtures/` (captured Sunday), no live printer.

- **`forge/adapters/bambu.py`** — from `send_bambu.py`: implicit-FTPS upload + MQTT start + AMS color map. `BambuAdapter(host, access_code, serial)`. Landmine: verify upload size before start (flaky-WiFi cancel). Fixtures: `bambu_a2l/mqtt_start.json`, `ftps_upload_trace.txt`.
- **`forge/adapters/ad5x.py`** — from `~/Desktop/3d_prints_tests/ad5x_tools/` (`ad5x.py` + `ad5x_mc.py`): 8899 single + 8898 status + **the multicolor IFS keystone** (`build_mappings()` nearest-RGB from gcode tool colors + live `/detail` slot state → `/printGcode` with `useMatlStation`+`materialMappings`). `AD5XAdapter(host, serial, check_code)`. Keystone = a regression fixture (`ad5x/print_gcode_request.json`, `ifs_slot_state.json`, `mono_without_ifs_case.txt`).
- **`forge/adapters/klipper.py`** — **write fresh** (no private source): Moonraker upload → `print/start` → `FIRMWARE_RESTART` recovery on "Lost communication with MCU" 400. `KlipperAdapter(moonraker_url)`. Fixtures: `ender/moonraker_upload.json`, `print_start.json`, `mcu_drop_400.txt`. (Real host today: REDACTED — see local `.forge_config.json`/env, not committed.)

---

# PHASE 3 — guardian + CLI wiring (away-sprint)

- **`forge/guardian.py`** — Amos: **deterministic reflexes** (over-temp / no-first-layer / stall / comms-drop / bed-not-confirmed-clear → fault-stop; run even with every model offline) + a **pluggable LLM-supervisor hook** (config → Grok) for judgment. **Pre-send veto:** the dispatcher calls `guardian.approve(job)` before `adapter.send` (the `store`/seam already anticipates this).
- **Wire `forge/cli.py`:** `forge send <file>` → build adapters from config → `Dispatcher.submit`; `forge status` → queue + studio-state.

## Notes for the away-sprint agents (Codex/Grok)
- Phase 1 has zero hardware need — do it first, anytime.
- Phases 2–3 need the Sunday `fixtures/` (Plan 0 Part B). AD5X multicolor is the keystone — treat its fixture as the acceptance test.
- Everything secretless in the public repo; Ryan's LAN specifics stay in the private deployment config.
