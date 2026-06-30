# Print Flow Runbook — download → print

For a **person or an agent**. Every step, every landmine. The golden rule: **slice in a proven GUI,
verify the gcode, send headless, watch the first layer.** Zero parameter loss between slicer and machine.

> File locations referenced here are defined in [`FILE_DISCIPLINE.md`](FILE_DISCIPLINE.md). Don't freelance paths.

---

## Step 1 — DOWNLOAD (get the model)

- **Source:** the licensed Patreon only (Cinderwing3D, MatMire Makes, Flexi Factory, …). We own the
  commercial-print license while subscribed — never print unlicensed models for sale.
- Download the creator's package (usually a `.zip` of STLs + sometimes a painted `.3mf`).
- **Save to:** `TELCHAR/01_models/<creator>/<sku>__<ModelName>.zip` (Drive).
  - On DAWES, the agent mirrors with: `rclone copy "gdrive:TELCHAR/03_ready_to_print/" ~/print_work/ready/`

## Step 2 — SLICE (GUI — OrcaSlicer 2.4.0, the stable path)

1. Open OrcaSlicer. **Select the correct printer profile** at top-left:
   `Bambu Lab A2L` · `Flashforge AD5X 0.4 nozzle` · `Ender-3 (Klipper)`. **Wrong profile = stripped/garbage output.**
2. Import the STL (or open the creator's `.3mf`).
3. **Multicolor:** paint the model, and set each filament's color to **match the physically loaded
   slot/AMS** (so the auto-mapper lands 1:1). Keep it to ≤ 4 colors on the AD5X.
4. Arrange on plate, supports, brim as needed.
5. **Slice.** Eyeball the preview — colors, supports, time.
6. **Export:** `File → Export G-code`.
   - **Ender →** `.gcode`  ·  **Bambu / AD5X →** `.gcode.3mf`
7. **Save to:** `TELCHAR/03_ready_to_print/` using the naming convention (see FILE_DISCIPLINE).

## Step 3 — INSPECT (verify the gcode BEFORE sending — the zero-param gate)

The agent never sends a file it hasn't checked. Extract `Metadata/plate_1.gcode` from the `.gcode.3mf`
(or read the `.gcode`) and confirm:

- **Multicolor:** `T0..T3` tool changes present · `WIPE_TOWER` present · `; filament_colour = #..;#..` lists
  each color · `; printer_model = ` matches the target printer.
- **Single-color:** one tool, correct profile, sane filament-used totals.
- **AD5X only:** the IFS slots currently loaded (`/detail` → `matlStationInfo.slotInfos`) **match the gcode's
  `filament_colour` order/colors.** `ad5x_mc.py` does this match automatically and prints the mapping.

## Step 4 — SEND (headless, per printer)

First mirror the file to the local working dir: `rclone copy "gdrive:TELCHAR/03_ready_to_print/<file>" ~/print_work/ready/`

| Printer | Command |
|---|---|
| **Bambu A2L** | `python3 ~/print_work/send_bambu.py ~/print_work/ready/<file>.gcode.3mf <ams_mapping e.g. 3,0,1> <name>` |
| **Ender 3** | upload to Moonraker (`POST :7125/server/files/upload`) → start (`POST :7125/printer/print/start?filename=<n>`). If it 400s with *"Lost communication with MCU"*: `POST :7125/printer/firmware_restart`, wait ~13 s, retry. |
| **AD5X — single color** | `cd ~/Desktop/3d_prints_tests/ad5x_tools && python3 ad5x.py send <file> --name "<Name>" --start` then the explicit `M6030` start. |
| **AD5X — multicolor** | upload first (`ad5x.py send <file> --name "<Name>.gcode.3mf"`), then **`python3 ad5x_mc.py "<Name>.gcode.3mf" ~/print_work/ready/<file>.gcode.3mf --fire`** (auto-maps tools→slots, sends `/printGcode` with `useMatlStation`). Dry-run without `--fire` first to eyeball the map. |

## Step 5 — PRINT + VERIFY

- **Beds must be CLEAR before any start.** This is the one thing the agent cannot see — confirm on camera.
- Confirm the printer transitions to *printing* (target temps climb, layer 0 begins).
- **Watch the first layer on camera:** adhesion good? For multicolor, do the slot colors actually swap?
  (`ad5x.py watch` shows `currentSlot` live.)
- If wrong: cancel immediately (printer touchscreen, `ad5x.py stop`, Moonraker cancel, or the kill switch).

## Step 6 — POST (close the loop)

- On finish: grab a **hero photo** → `TELCHAR/04_prints/<sku>/` for the site/thumbnail.
- The **YT flow** (`yt-flow.timer` → `yt_apply.py`) auto-refreshes the live title/description from the floor.
- Log the print (model, printer, material, time, outcome) — future: the per-SKU Notion DB.

---

## Per-printer landmines (memorize these)

| Printer | Landmine | Fix |
|---|---|---|
| **Bambu A2L** | WiFi flaky (278 ms↔2 s, 25% loss) → upload **cancels** | persistent `curl --retry`; improve the printer's WiFi |
| **Bambu A2L** | `forge/bambu.py` upload uses explicit FTPS (hangs) + `use_ams:false` | use `send_bambu.py` (implicit FTPS + AMS map) |
| **Ender 3** | Klipper drops MCU comms → won't start | `firmware_restart`, confirm kill switch ON |
| **AD5X** | multicolor prints **mono** | the *start* must carry `useMatlStation`+`materialMappings` → `ad5x_mc.py` |
| **AD5X** | `M23` only *selects* a file | send explicit `M6030` (single) or `/printGcode` (multi) |
| **AD5X** | `completed` state blocks a new print | clear/ack the finished job on the touchscreen → `ready` |
| **AD5X** | flexible TPU buckles at slot load | re-run the load cycle on the printer; not a send bug |
| **all** | wrong printer profile in the slicer | strips tool changes / breaks the file — check top-left dropdown |
