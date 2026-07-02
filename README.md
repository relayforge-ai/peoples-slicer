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

`ad5x_mc.py` reads the gcode's tool colors + the *live* IFS slot state and auto-builds that map.
Even Orca-Flashforge only does this through a manual GUI dialog — **we made it headless and
self-mapping.** Pillars #1 and #2, proven.

## Current Tooling

| Tool | Printer | Does |
|---|---|---|
| `send_bambu.py` | Bambu A2L | curl implicit-FTPS upload + MQTT start + AMS color map |
| Moonraker calls | Ender 3 | upload + `/printGcode` start + FIRMWARE_RESTART recovery |
| `ad5x_mc.py` | AD5X | **headless multicolor** — auto-maps tools→IFS slots, `/printGcode` |
| `ad5x.py` / `ad5x_print.py` | AD5X | single-color send (8899) + status/watch |
| `print_flow.py` | all | live floor → current-prints card + high-CTR title |

## Status & Roadmap

- ✅ **Phase 1 (the unlock):** headless send + zero-param multicolor for all three printers. *Proven live.*
- ✅ **Phase 2 (the fork):** MIT repo with `forge` engine — classifier, queue, dispatcher, AD5X/Bambu/Klipper adapters, Amos guardian, `forge send`/`status` CLI. *55 tests green.*
- ⏳ **Phase 3 (the product):** discover + review + viewer + one-command install; the mom test.

## Credits

- [`GhostTypes/ff-5mp-api-py`](https://github.com/GhostTypes/ff-5mp-api-py) (MIT) — the reverse-engineered
  FlashForge API that revealed the `materialMappings` protocol.
- [`FlashForge/Orca-Flashforge`](https://github.com/FlashForge/Orca-Flashforge) — the open fork confirming the struct.
- OrcaSlicer / Bambu Studio / PrusaSlicer lineage.

*Living north star — we document changes + improvements as we go. See [`docs/PRINT_FLOW.md`](docs/PRINT_FLOW.md)
and [`docs/FILE_DISCIPLINE.md`](docs/FILE_DISCIPLINE.md).*
