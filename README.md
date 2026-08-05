# 🦞 The People's Slicer

> **The Apple-iOS of slicing software.** Buy an affordable, high-quality printer (Bambu A2L,
> FlashForge AD5X) and have a personal agent (a *lobster*) operate it for you — as a life-hack
> or a business. MIT, open-source, agent-first. For them and for us.

*Source vision: "The People's Slicer", R. Anderson — mirrored to Notion when access clears.*

## The Vision

3D printing is *mostly* ready for autonomy — but it's still full of bugs and little landmines.
This is the attempt to file those down to nothing. The biggest win is a dead-simple
**install → import → slice → print** flow that a 74-year-old with a laptop and an agent could run.

No bells and whistles: a simple project viewer, a few tools, and **very, very strong CLI
interfaces to every printer we can reach.**

## Three Pillars (do these exceptionally well)

1. **Network/CLI to any printer** — connect and operate a variety of printers headless, over the LAN.
2. **Zero parameter loss** — high-quality sliced projects sent via CLI with *nothing* dropped
   between the slicer and the machine.
3. **Mom-simple** — anyone could make anything within the printer's limits using just a laptop + an agent.

## Prerequisites (read this before the quickstart)

The GUI path (below) needs nothing beyond OrcaSlicer itself. The **headless path** — the
one an agent actually runs, since an agent cannot click through a GUI — needs a few things
the rest of this README assumes you already have. None of it is exotic, all of it is a
real, one-time setup cost:

- **`pipx`, not `pip install .`** — a stock Ubuntu/Debian box (PEP 668, "externally managed
  environment") refuses a plain `pip install` outside a venv. `apt install pipx` first if
  it's not already there.
- **`xvfb-run`** (`apt install xvfb`) — both BambuStudio and OrcaSlicer are GUI applications
  that still need a real (virtual, in this case) X display even in their "headless" CLI
  slice mode. `forge` fails loudly and immediately if this is missing, which is more than
  can be said for some of the other gaps below.
- **The BambuStudio AppImage** (for `a1mini`/`a2l`) — a hard dependency, not mentioned
  anywhere else in this doc. Grab the release matching your target printer's profile support
  from [bambulab/BambuStudio releases](https://github.com/bambulab/BambuStudio/releases),
  then extract its bundled vendor profiles:
  ```bash
  chmod +x BambuStudio_*.AppImage
  ./BambuStudio_*.AppImage --appimage-extract
  export BAMBU_STUDIO_BIN=$(pwd)/BambuStudio_*.AppImage
  export BAMBU_PROFILES=$(pwd)/squashfs-root/resources/profiles/BBL
  ```
- **The Orca-Flashforge fork** (for `ad5x`/`ender`) — from
  [FlashForge/Orca-Flashforge releases](https://github.com/FlashForge/Orca-Flashforge/releases),
  extract the same way. **Gotcha:** this fork's binary is named `flash studio` (lowercase,
  with a space), not `orca-slicer` — `forge` looks for `bin/orca-slicer` inside the extracted
  tree, so symlink it after extracting:
  ```bash
  ./Flash.Studio_*.AppImage --appimage-extract -o ~/orcaslicer   # -> ~/orcaslicer/squashfs-root
  ln -s "flash studio" ~/orcaslicer/squashfs-root/bin/orca-slicer
  ```
- **STL units** — STL has no unit standard; 3D-printing tooling universally assumes the raw
  numbers are millimeters. If your STL was exported in meters (common if it came out of
  Blender without an explicit unit-scale conversion at export time), the slicer will
  silently try to print an object a thousand times smaller than intended and fail with
  *"No layers were detected"* — a real geometry-shaped error message for what is actually a
  units bug. Sanity-check your STL's raw bounding box against the target printer's bed size
  in mm before slicing if that error ever shows up.

## Quickstart

**Headless (what an agent actually runs)** — five commands, once the prerequisites above are in place:

```bash
# 1. Install
pipx install git+https://github.com/relayforge-ai/peoples-slicer     # or, from a clone: pipx install .

# 2. Slice, headless (REL-600/601) — no GUI, no human required
forge slice model.stl --printer a1mini --dry-run             # resolve profiles + fit-check only
forge slice model.stl --printer a1mini -o out.gcode.3mf       # the real slice
forge slice model.stl --printer a2l --auto-refit              # scale to fit if oversized
forge harvest                                                  # index Orca vendor profiles

# 3. Point at a printer — every credential is read from the ENV; nothing is stored in the repo
export AD5X_HOST=192.168.4.37 AD5X_SERIAL=… AD5X_CHECKCODE=…         # FlashForge AD5X
#  or  export BAMBU_HOST=… BAMBU_ACCESS_CODE=… BAMBU_SERIAL=…        # Bambu A2L / A1 mini
#  or  export MOONRAKER_URL=http://192.168.4.49:7125                 # Ender 3 / Klipper

# 4. Find printers on the LAN (concurrent, streams results as found — a full /24 takes
#    seconds, not minutes) and check a sliced file before it ever hits the machine
forge discover --save ad5x
forge review out.gcode.3mf            # audits the finicky, easily-dropped params for that printer
forge send    out.gcode.3mf --dry-run # classify + review only, don't send

# 5. Send — headless, zero parameter loss (AD5X multicolor IFS map auto-built).
#    Live send requires --bed-confirmed (fail-closed guardian) — the one thing an agent
#    cannot see for itself is whether the physical bed is actually clear.
forge send out.gcode.3mf --bed-confirmed
forge status                          # what's queued / printing

# One call, slice through send:
forge slice-send model.stl --printer ad5x --dry-run          # slice + classify, no send
forge slice-send model.stl --printer ad5x --bed-confirmed    # live send (guardian)

# Hands-off: drop files in a folder and forge routes them for you
forge watch --dir ~/forge-drop
```

**GUI (a human at a desktop, or when you'd rather slice by hand):** open OrcaSlicer, slice
and export as usual, then `forge review` / `forge send` the exported file exactly as in
steps 4–5 above — `forge` handles everything *after* the slice either way.

`forge --help` lists every subcommand. **No keys are ever written to disk in the repo** — the
adapter reads `AD5X_*` / `BAMBU_*` / `MOONRAKER_URL` (or a `FORGE_CONFIG` file you control) at runtime.

## Why It Exists — the landmines are real

Found the hard way, live, in one night (2026-06-29 → 30):

- Bambu's flaky WiFi silently **cancels uploads** mid-transfer.
- Klipper drops MCU comms and **refuses to start** until a firmware restart.
- The AD5X **ignores all 101 tool changes and prints mono** unless the *start call* carries the IFS map.
- Mainline OrcaSlicer drops **FlashForge metadata** the printer's ETA/API expect.

Every one of these is a parameter or handshake the GUI hides and the CLI must make bulletproof.
**That gap is the product.**

## Architecture

- **MIT, open-source**, under the `relayforge-ai` org. Stands on OrcaSlicer + the `Orca-Flashforge`
  fork + `GhostTypes/ff-5mp-api-py` (all open).
- **CLI-first.** Slicing can stay in a proven GUI (OrcaSlicer) for now — the magic is the **headless
  send layer** with per-printer adapters that lose zero parameters.
- **Printer adapters (today):** Bambu A2L (implicit-FTPS upload + MQTT start + AMS map),
  Ender 3 / Klipper (Moonraker upload + start + FIRMWARE_RESTART recovery),
  FlashForge AD5X (8898 `/printGcode` with `useMatlStation` + `materialMappings`).

## 🔑 The Keystone — AD5X Headless Multicolor (SOLVED 2026-06-30)

The AD5X printed mono not because of the slice or the hardware, but because our headless
`M23`/`M6030` start sent **none of the IFS mapping**. The fix is a single API call:

```
POST http://<printer>:8898/printGcode
{ serialNumber, checkCode, fileName,
  useMatlStation: true,
  gcodeToolCnt: N,
  materialMappings: [ { toolId 0-3, slotId 1-4, materialName,
                       toolMaterialColor "#RRGGBB", slotMaterialColor "#RRGGBB" }, … ] }
```

`forge/adapters/ad5x.py` reads the gcode's tool colors + the *live* IFS slot state and
auto-builds that map. Even Orca-Flashforge only does this through a manual GUI dialog —
**we made it headless and self-mapping.** Pillars #1 and #2, proven.

## Current Tooling

Everything below is one `forge` CLI (`forge send` / `forge slice` / `forge discover` / ...)
over a set of per-printer adapter modules — there are no standalone scripts to run directly;
if you find a doc or an old note naming one (`send_bambu.py`, `ad5x_mc.py`, `ad5x_print.py`,
`print_flow.py`, ...), it's describing an earlier, pre-`forge` toolset — the table below is
current as of this README.

| Adapter | Printer | Does |
|---|---|---|
| `forge/adapters/bambu.py` | Bambu A1 mini / A2L | implicit-FTPS upload + MQTT start + AMS color map |
| `forge/adapters/klipper.py` | Ender 3 | Moonraker upload + `/printGcode` start + FIRMWARE_RESTART recovery |
| `forge/adapters/ad5x.py` | FlashForge AD5X | **headless multicolor** — auto-maps tools→IFS slots, `/printGcode` (`useMatlStation`), plus single-color send + status/watch |

Drive all of them through `forge send` / `forge status` / `forge watch` — the adapter is
selected automatically from the printer key, you never invoke one directly.

## Status & Roadmap

- ✅ **Phase 1 (the unlock):** headless send + zero-param multicolor for all three printers. *Proven live.*
- ✅ **Phase 2 (the fork):** MIT repo with `forge` engine — classifier, queue, dispatcher, AD5X/Bambu/Klipper adapters, Amos guardian, and the full `forge discover / review / send / status / watch` CLI. *98 tests green.*
- ⏳ **Phase 3 (the product):** a simple project viewer + one-command install + a 30-second demo; the mom test.

## Credits

- [`GhostTypes/ff-5mp-api-py`](https://github.com/GhostTypes/ff-5mp-api-py) (MIT) — the reverse-engineered
  FlashForge API that revealed the `materialMappings` protocol.
- [`FlashForge/Orca-Flashforge`](https://github.com/FlashForge/Orca-Flashforge) — the open fork confirming the struct.
- OrcaSlicer / Bambu Studio / PrusaSlicer lineage.

*Living north star — we document changes + improvements as we go. See [`docs/PRINT_FLOW.md`](docs/PRINT_FLOW.md)
and [`docs/FILE_DISCIPLINE.md`](docs/FILE_DISCIPLINE.md).*
