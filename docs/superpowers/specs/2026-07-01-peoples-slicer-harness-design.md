# The People's Slicer — Harness Design (v0.1 sprint spec)

> **Version:** v1.0 · **Date:** 2026-07-01 · **Status:** DRAFT — awaiting Ryan's review
> **Owner:** Ryan Anderson · **Author:** Claude (Opus 4.8), brainstormed with Ryan
> **Repo:** `~/peoples-slicer` (public, MIT) · **Canonical docs home:** this repo (Notion mirrors)
> **Umbrella / mission:** The People's Slicer · **Product / harness:** **Telchar's Forge** (CLI: `forge`)

---

## 0. One sentence

**You slice in Orca. You drop the file in. You stay in your chair** — an open-source *harness*
that discovers every printer on your LAN, reviews and improves the finicky parameters, sends the
job headless with zero parameter loss, and hands it to an AI operator that runs the print safely.

It is **not a slicer and not a replacement for Orca.** It is the missing layer that runs
everything *after* the slice.

---

## 1. The reframe (what this project actually is)

Slicing is the fun, creative part — scaling a model, arranging it, making it *cool*. Creators like
doing it, and OrcaSlicer / Bambu Studio / Orca-FlashForge all look alike, so the muscle memory
transfers. **We keep that.** What everyone hates and takes years to learn is the "--- after ---":
which folder, which SD card, bed temps, extruder temps, brim size, wall thickness, getting Orca
onto Klipper through a Raspberry Pi. **That gap is the product.**

Positioning (this is a feature, and it is deliberately humble): *"Not a replacement for Orca. The
harness that runs everything after."* It rides Orca's familiarity instead of fighting it. Download
from GitHub / the site / YouTube, keep using Orca, add the one missing layer. Lowest possible
barrier to entry — which is exactly what makes it a **customer-acquisition funnel** for
telchar.relayforge.tools: someone pulls the tool because their AD5X won't print multicolor
headless, it *just works*, and every touchpoint (README, `--help`, viewer footer) points home.

### Brand architecture (the funnel, made explicit)

- **The People's Slicer** = the umbrella / mission: the MIT project, the GitHub banner, the
  "slicing-for-everyone, agent-first" movement. Welcoming, community-facing — the reason a stranger
  stars it.
- **Telchar's Forge** = the product you run: the harness that *forges* a sliced file into a finished
  print (Telchar the smith → the forge where raw becomes finished). CLI command: `forge`. This
  carries the Telchar brand into every session and points home.
- Headline: **"The People's Slicer — powered by Telchar's Forge."** Tagline: *"you slice, it does
  the rest."*

**Funnel touchpoints (tasteful — a tool that feels like adware stops being a funnel):**
README hero + `forge --help` banner (*"made in the Telchar studio → telchar.relayforge.tools"*) ·
viewer footer (*"want a lobster to run your printer? → site"*) · one gentle line on print-complete
pointing to the studio/catalog · GitHub sponsor/org link → RelayForge · and the **Telchar-the-smith
capstone print is itself branding** — the namesake on the shelf in every stream shot.

---

## 2. North star, as an architecture rule

**"A print shop run by Haiku-level intelligence."** This is not a cost note — it is *the* constraint
that designs everything: **no hard inference at runtime.** Every decision the operating agent faces
must already be answered — in a deterministic table, a playbook, or a typed config — *before* it
runs. The cheap agent does not reason its way through "the AD5X printed mono"; it reads a line in
the screenplay: *"AD5X + multicolor → the start call MUST carry the IFS map; here is how it is built;
here is how you verify it took."*

Concretely: the **public reference operator brain is Gemini** (a RelayForge lobster on Gemini makes
a print). So the real, testable meaning of "Haiku-level" is: **could Gemini execute this playbook
with zero guessing?** That is the acceptance test for every doc and every code path.

Therefore **the documentation IS the product.** The deliverable is a *screenplay*: deterministic
code that loses zero parameters, plus per-printer playbooks that encode every landmine and its
resolution so completely that a small model — or a 74-year-old with a laptop and a lobster — never
has to infer anything.

### Model lanes (deliberately mixed — for supervision diversity)

| Lane | Model | Role |
|------|-------|------|
| **Operator (public)** | **Gemini** | Executes the screenplay. Runs on the cheap mini PC. Zero hot-path inference. |
| **RelayForge premium** | **Fable 5** | Ryan's invested inference for the RelayForge-side brains. |
| **AI interactions** | **DUNE / Seurat** (local, sovereign) | Briggs / chat / voice, when fully implemented. Seurat = lead orchestrator + approver. |
| **Amos Dawes (safety)** | **Grok** (OpenClaw agent on DAWES) | Printer safety + monitoring supervisor. **Different family from the operator on purpose** — the checker must not share the doer's blind spots. |
| **Sheldon Io (stream health)** | *(deferred — Telchar side)* | Stream/encoder resilience guardian. Out of scope this sprint. |

The operator interface stays **model-neutral**, so "Gemini for them / Fable 5 for us" is a config
line, never a fork.

---

## 3. Scope (v0.1)

**Option A — send-layer-first, with a documented slice seam.** Confirmed direction.

**In v0.1:**
1. **DISCOVER & CONNECT** — LAN scan that recognizes anything 3D-printer-shaped; enter the access
   code / Pi password *once*, persisted forever.
2. **REVIEW & IMPROVE (deterministic)** — profile + rule based audit of the finicky parameters
   (brim / walls / supports / temps) for *this printer + material*; a "review in the middle" the
   user accepts or nudges. **No spatial reasoning** — the user already arranged the model.
3. **SEND & OPERATE** — reliable headless send, zero parameter loss, per-printer landmine handling;
   then the AI operator takes over with Amos watching safety.
4. **Simple project viewer** — see what is queued/printing, drop a file in.
5. **The screenplay** — repo-canonical playbooks + OPERATING + SAFETY docs.
6. **Telchar site-flow seams** — stubbed programmatic interface so agents can drive the full
   order→print flow later without a rewrite.

**Deferred to v0.2 (documented seams, not built):**
- The **freeform LLM slice-advisor** ("make my slice smarter"). v0.1's review is deterministic only.
- **Bundled headless slicing** (STL→gcode inside the harness). Slicing stays in Orca; the `slice`
  command is a stable *interface* with a Bambu-Studio-CLI backend behind it, hardened later.
- One-command install / full "mom-test" onboarding polish (Phase 3).

**Out of scope:** replacing Orca; the Telchar stream stack (Sheldon Io); customer intake form UI.

---

## 4. Architecture — the public / private split (key structural decision)

There are two existing bodies of proven code, and they have **different trust levels**:

- **`~/print-router/`** (private) — the deterministic router, **built, 35 tests green**:
  `classifier.py` (routing tree), `reader.py` (header/footer parse), `jobqueue.py` (crash-recoverable
  FIFO + dedupe), `dispatcher.py` (idle→send / busy→queue / quarantine + event seam),
  `drive_inbox.py`, `adapters/ad5x` (live-validated). Holds **LAN IPs and reaches
  `~/.relayforge_secrets`** — explicitly never public.
- Scattered adapter tools — `send_bambu.py` (in `print_work/` + `makerlobster-catalog/`),
  `~/Desktop/3d_prints_tests/ad5x_tools/` (`ad5x.py`, `ad5x_mc.py`, `ad5x_send.py`,
  `ad5x_start.py`, `ad5x_print.py`), Moonraker calls, `makerlobster-catalog/print_flow.py`.

**The design: extract the generic, secrets-free *engine* into the public `peoples-slicer` harness;
keep Ryan's specific deployment (LAN IPs, access codes, SKU routing, Mongo, Drive, YT flow) as
private config that *consumes* the public engine.**

```
PUBLIC  ~/peoples-slicer   (MIT — everyone runs this)
  forge/
    discover.py     LAN scan + printer fingerprint + credential store (enter once)
    classifier.py   gcode header/footer → {printer, material, colors, est_time, est_grams, bed_fit}
    review.py       deterministic profile/rule lint → suggestions the user accepts/nudges
    jobqueue.py     crash-recoverable per-printer FIFO + dedupe        (from print-router)
    dispatcher.py   idle→send / busy→queue / quarantine + event seam   (from print-router)
    guardian.py     Amos rules: deterministic reflexes + pluggable LLM-supervisor hook (→ Grok)
    adapters/
      base.py       the contract: status()/send()/watch()/stop()
      bambu.py      implicit-FTPS upload + MQTT start + AMS map     (from send_bambu.py)
      ad5x.py       8899 single + 8898 status + multicolor IFS map  (from ad5x_tools)
      klipper.py    Moonraker upload + start + FIRMWARE_RESTART recovery
    api.py          library + stubbed HTTP API (the Telchar-agent seam)
    cli.py          `forge discover | review | send | status | watch`
  viewer/           simple project viewer (queued/printing, drop target)
  docs/
    playbooks/{bambu-a2l,ad5x,ender-klipper}.md   the per-printer screenplay
    OPERATING.md    the Gemini/Haiku runbook (executable with zero inference)
    SAFETY.md       Amos Dawes rules (deterministic reflexes + escalation)
  fixtures/         captured hardware truth — tests run with NO printer

PRIVATE ~/print-router (or a config repo)   (Ryan's Telchar deployment)
  config: LAN IPs, access codes, SKU→printer routing, Mongo write-through,
          Drive (03_ready_to_print contract), YT flow, Telegram alerts
  → imports the public forge engine; adds nothing the public tool needs
```

**The key abstraction is the adapter contract** (`base.py`): three printers, one interface
(`status()` → idle/printing/attention/offline; `send(file, mapping, start)`; `watch()`; `stop()`).
The engine never knows printer specifics — it asks "are you free?" and "take this file." That is
what let the Ender/Bambu adapters drop in beside the proven AD5X one, and it is what lets a
community contributor add a Prusa/Klipper variant without touching the core.

### Reference deployment host — `ganymede` (Windows 11)

The mini PC on the LAN (arrived 2026-06-28) is the reference host: **`ganymede`, Windows 11 24H2**,
on the same LAN /24 as the printers, reachable over Tailscale. (Real LAN/Tailscale addresses + the
tailnet name live in the private deployment config — never this public repo.)
"A cheap mini PC + Gemini + our harness = a print shop" made literal — and Windows is *right* for
the mom-test, because that is what hobbyists and Orca already run.

**Windows implications (bake into the deploy layer):**
- **No `systemd --user`.** The watcher/daemon runs as a **Windows Service / Task Scheduler task
  (NSSM is the pragmatic wrapper)**, or under **WSL2** if we want the Linux tooling. Decision in §14.
- **File watching must be cross-platform** — use the `watchdog` library, not raw inotify.
- **Paths, line endings, venv** — the engine is pure-Python and portable; keep OS-specific bits
  (service install, path roots) in the private deploy config, not the public engine.
- **Tailscale is installed** → clean remote management / status without opening LAN ports.
- **Currently offline** (last seen Jun 29, "not connected") — must be brought online for the
  Phase-0 capture and to serve as the runtime host.

---

## 5. Data flow (drop → done)

```
Orca ▸ Export G-code ─────────────► drop target (watched folder / viewer drop)
                                        │
  discover.py (already connected, enter-once creds) knows every printer on the LAN
                                        │
  classifier.py: header/footer → {printer, material, colors, est_time, est_grams, bed_fit}
                                        │
  review.py: deterministic lint vs the printer+material profile
             → "brim 0 → suggest 5mm; wall 2 → ok; supports off → risk on this overhang"
             → USER sees the review, accepts or nudges (re-slice only these params, no re-arrange)
                                        │
  guardian.py PRE-SEND HOOK: Amos (Grok) may VETO before anything is sent
                                        │
  dispatcher.py:  idle → adapter.send(start) ; busy → queue/<printer>/ (FIFO, dedupe)
                                        │
  adapter runs the printer-specific landmine-safe send (see playbooks)
                                        │
  OPERATE: AI operator watches first layer; Amos monitors; events → jobs.jsonl (+ Mongo, private)
```

`jobs.jsonl` + `queue_state.json` are the **agent seam**: append-only event log the operator and
Amos read, and the Telchar site flow attaches to later with no rework.

---

## 6. The screenplay — per-printer landmines (consolidated from Notion)

These tables are the heart of "docs are the product." Each becomes a `docs/playbooks/*.md` entry;
each landmine gets a **detection** and a **deterministic resolution** so Gemini never infers.

### Bambu A2L — production default (PLA + stiff, AMS 4-color)
| Landmine | Detection | Resolution |
|----------|-----------|------------|
| Flaky WiFi silently **cancels uploads** mid-transfer | upload byte count < file size / no confirm | persistent `curl --retry`; verify size post-upload before start; improve printer WiFi |
| `forge/bambu.py` explicit-FTPS **hangs** + `use_ams:false` | legacy path | use the `send_bambu.py`-derived adapter (implicit-FTPS + MQTT + AMS map) |
| Build volume: **height 325 mm** (confirmed); X/Y ~256×256 (confirm) | — | bed-fit uses 256×256×**325**; confirm X/Y before trusting tall-model fit |

### AD5X — flexible/TPU machine, multicolor via IFS station (the keystone)
| Landmine | Detection | Resolution |
|----------|-----------|------------|
| Multicolor prints **mono** | start call missing IFS map | start MUST carry `useMatlStation:true` + `materialMappings[]` via `/printGcode` (8898) — `ad5x_mc.py` auto-builds the map from gcode tool colors + live IFS slot state |
| `M23` only *selects*, doesn't print | job selected, not started | single-color: send `M6030`; multicolor: `/printGcode` |
| `completed` state **blocks** a new print | status = completed | clear/ack on touchscreen → `ready` (physical; agent flags, never forces) |
| Flexible TPU **buckles** at load | load fault / pause | re-run load cycle on the printer (physical) |

### Ender 3 Pro (Klipper via Moonraker) — folk-art / spliced premium lane
| Landmine | Detection | Resolution |
|----------|-----------|------------|
| Klipper **drops MCU comms**, refuses to start | Moonraker 400 "Lost communication with MCU" | `firmware_restart`, wait ~13 s, retry; kill switch ON |
| Orca→Klipper→Pi setup is "nuts hard" | onboarding | **discover.py owns this**: fingerprint Moonraker (7125), enter Pi creds once, persist |

### All printers
| Landmine | Detection | Resolution |
|----------|-----------|------------|
| Wrong slicer profile strips tool changes | `printer_model` header ≠ target | classifier rejects → `failed/` + alert; **never guess a printer** |
| Bed not clear before start (agent can't see it) | — | camera/human confirm gate before any start; SAFETY.md hard rule |

**Routing tree** (deterministic, material is the top-level switch — printers are dedicated by
material): flexible/TPU → AD5X · stiff multicolor → Bambu A2L · stiff single → Bambu default, Ender
opt-in (folk-art/spliced). Then: how big → scale + bed-fit; how fast → profile. In v1 the routing
is fixed at slice time by the OrcaSlicer profile that stamps `printer_model` into the header.

---

## 7. Amos Dawes — the safety guardian

`guardian.py` is **deterministic reflexes** (no model needed, always-on, can't depend on any LLM
being up) + a **pluggable supervisor hook** for judgment calls (points at Grok; swappable by config):

- **Reflexes (deterministic, hard rules — SAFETY.md):** over-temp, no-first-layer-detected,
  stall/no-progress, comms-drop, bed-not-confirmed-clear → **fault-stop, never auto-resume a
  physical fault.** These run even if every model is offline.
- **Pre-send veto hook:** Amos may reject a job *before* `adapter.send` (the print-router seam
  already anticipates this). Mixed-model: Amos on Grok, operator on Gemini — independent failure
  modes by design.
- **Seurat is lead approver:** Amos and "grok build" both gate through Seurat in the full mesh;
  v0.1 stubs this as a typed approval interface.

This is the MANDOS process-safety line made operational: **nothing prints unattended without a
different mind than the operator having the ability to stop it.**

---

## 8. Discovery & connection (the enter-once promise)

`discover.py`:
- **Scan** the LAN for printer fingerprints: Bambu (SSDP/MQTT), FlashForge/AD5X (8898/8899),
  Klipper (Moonraker 7125), OctoPrint (5000/API), generic (mDNS `_printer._tcp`, common ports).
- **Recognize** model where possible; surface unknowns as "3D-printer-shaped, needs a code."
- **Credential store:** enter access code / Pi password **once**, encrypted at rest, persisted —
  "it is now connected, always there." Solves the specific pain that vendor slicers each see only
  *some* of the printers (Orca misses the too-new A2L; FlashForge misses the A2L; Bambu ignores the
  AD5X). The harness sees them all.
- **Cross-platform** (runs on ganymede/Windows): pure sockets + `zeroconf`; no OS-specific scan.

---

## 9. Telchar site-flow seams (stub now, wire on return)

The harness must be drivable by agents, not just humans. `api.py` exposes the same engine as a
**library + a stubbed HTTP API** so the Telchar site can later run order → slice → route → print →
fulfill through the identical core. This sprint: define the typed calls and no-op/stub the
site-specific ends. Every Telchar touchpoint is labeled `# TELCHAR SEAM` in code and listed in
`OPERATING.md`. Mongo write-through and the SKU/`03_ready_to_print` Drive contract stay **private**
(they belong to Ryan's deployment, not the public tool).

---

## 10. Phase 0 — capture hardware → fixtures (NOW → Sunday)

The away-sprint is hardware-less; building adapters needs printer responses to test against. **This
week, while hands are on hardware, freeze real truth into `fixtures/`:**

- [ ] Golden sliced gcode per printer (known models) → the zero-parameter-loss diff baseline.
- [ ] AD5X `/printGcode` request+response; live IFS `matlStationInfo.slotInfos` JSON; a real
      `materialMappings` map.
- [ ] Bambu MQTT start payload + implicit-FTPS upload trace; the flaky-WiFi cancel case.
- [ ] Moonraker upload → `print/start` sequence; the "Lost communication with MCU" 400 + recovery.
- [ ] The 2026-06-29→30 failure cases frozen as **regression fixtures** (mono-without-IFS, silent
      cancel, MCU drop).
- [x] **Mini PC basics:** `ganymede`, Windows 11 24H2 (10.0.26100.3476) — **online + connected to
      Tailscale as of 2026-07-01** ✓ (LAN/Tailscale addresses recorded in the private deployment
      config, not this public repo). *Still needed:* Python version, is Mongo installed/running.
- [x] Bambu A2L build **height = 325 mm** (Ryan, 2026-07-01). *Still needed:* X/Y (likely 256×256).

Capture these and three agents can build + test the entire harness against recorded truth for three
weeks; validate on real metal night-1 home.

---

## 11. Phasing & the funnel

- **Phase 0 (now→Sun, hardware):** capture fixtures (above); bring ganymede online.
- **Phase 1 (vacation, agents, hardware-less):** extract print-router + scattered adapters → public
  `forge` engine; add discover + deterministic review + guardian hook + viewer; write the
  screenplay; tests against fixtures + dry-run mode; **every touchpoint points home to the site**;
  start marketing (README, GitHub, YT).
- **Phase 2 (home, hardware):** validate on real metal; **Telchar-the-smith ceremonial first
  multicolor print**; public MIT launch.

---

## 12. Error handling & testing

- Unparseable/missing header → `failed/` + alert; **never guess** a printer.
- Printer offline at send → keep queued, backoff retry, alert after N.
- Bed-fit fail (model > bed) → `failed/` + alert; **no silent auto-scaling**.
- Physical fault at send (TPU load-fail) → adapter `attention`; flag + alert; **no auto-resume**.
- Single-client politeness: AD5X (one control session) + Bambu (one MQTT/cam client) — adapters
  open/close cleanly, never starve the camera bridges.
- Crash recovery: rebuild from `queue_state.json` + dirs; re-poll; never double-start.
- **Testing:** classifier/queue/dispatcher unit tests (already 35 green in print-router); adapters
  against **fixtures** (mock endpoints, captured payloads) — no printer needed; **dry-run
  (`--no-send`)** safe while printers are mid-print; e2e on real metal night-1 home.
- **Mom-test:** a fresh user on the mini PC can discover → connect (enter code once) → drop an
  Orca file → accept the review → print, with no manual SSH/scp and no learned parameter knowledge.

---

## 13. Success / definition of done (v0.1)

1. One `forge` CLI discovers and connects all three printers on the LAN (enter code once).
2. Drop an Orca-exported file → deterministic review → headless send → print, **zero parameter
   loss**, on all three printers (validated night-1 home; fixtures green while away).
3. AD5X **multicolor headless** works via auto-built IFS map (the keystone), covered by a
   regression fixture.
4. Amos deterministic reflexes + Grok pre-send veto hook wired (model-neutral).
5. Public MIT repo, screenplay docs in-repo, Notion mirrored, **every touchpoint links home**.
6. Telchar-the-smith printed as the launch hero.

---

## 14. Decisions (resolved 2026-07-01; residuals noted)

1. **Public/private split** — RESOLVED: generic engine goes public in `peoples-slicer` (Telchar's
   Forge); `print-router` becomes the private config/deployment that imports it — keeps LAN IPs,
   Mongo, Drive, YT flow out of the public repo.
2. **Name/brand** — RESOLVED (Ryan, 2026-07-01): umbrella **The People's Slicer** + product
   **Telchar's Forge** (CLI `forge`), tagline *"you slice, it does the rest."* Minor open item: if
   the `forge` binary name collides on users' machines, fall back to `telforge`.
3. **Mongo in public engine?** — RESOLVED: NO. Mongo write-through stays private; the public engine
   emits `jobs.jsonl` + a pluggable event sink the Telchar deployment wires Mongo into.
4. **ganymede runtime model** — RESOLVED: **native Windows + `watchdog`** (no WSL install = more
   mom-simple); the Python engine stays OS-agnostic so power users can run it on Linux.
5. **Bambu A2L build volume** — height **325 mm** confirmed; X/Y still to confirm (likely 256×256).
6. **Viewer scope** — RESOLVED: v0.1 = read-only status + drop target only; live controls ride the
   `/drive` PTZ pattern in a later version.

---

## 15. The capstone (the fun one)

**Telchar of Nogrod** — the dwarf-smith who forged Narsil and the knife Angrist — gets a bust in
his own shop. It doubles as the perfect launch artifact: *the first model The People's Slicer ever
prints end-to-end, headless, is Telchar himself* — multicolor, so it drives the AD5X IFS keystone
straight through the pipeline. The namesake blessing the tool. Find/adapt an STL in Phase 0/2.

---

## References

- `~/peoples-slicer/README.md` — the vision / north star
- Notion: *The People's Slicer* · *Print Flow Runbook — download → print* · *File Discipline —
  TELCHAR organization* · *MakerLobster #1 — Slicer → Save → Route (Deterministic Print Router)* ·
  *MakerLobster — Architecture & Decisions*
- `~/print-router/` (private) — proven deterministic router core (35 tests green)
- `~/Desktop/3d_prints_tests/ad5x_tools/` — AD5X CLI (incl. `ad5x_mc.py` multicolor keystone)
- `send_bambu.py` (Bambu adapter source) · `makerlobster-catalog/print_flow.py`
