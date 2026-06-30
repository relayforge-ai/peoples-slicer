# File Discipline — TELCHAR organization

Strong discipline = an agent can find, slice, send, and *re-print* anything without guessing.
**One home for each kind of file. Numbered folders sort in workflow order. Consistent names.**

> Parent folder `TELCHAR` already created in Google Drive by Ryan. rclone remote = `gdrive:`.

## Google Drive — `TELCHAR/`

```
TELCHAR/
├── 00_inbox/            ← drop zone; un-filed downloads land here, get sorted out daily
├── 01_models/           ← downloaded licensed model PACKAGES (raw, by creator)
│   ├── cinderwing3d/
│   ├── matmire/
│   └── flexi_factory/
├── 02_projects/         ← slicer PROJECT files (.3mf paint-ready / working), by sku
├── 03_ready_to_print/   ← SLICED, send-ready files. THE PIPELINE PULLS ONLY FROM HERE.
├── 04_prints/           ← printed archive + hero photos, by sku (for site/thumbnails)
└── 05_docs/             ← runbooks + the vision (mirror of peoples-slicer/docs)
```

**The contract:** the headless pipeline only ever reads `03_ready_to_print/`. A file there is a
promise: *sliced, inspected, ready to fire.* Nothing half-baked goes in that folder.

## Naming conventions

**SKU** = `<creator-prefix>-<model-slug>`  (prefixes: `cw-` Cinderwing3D, `mat-` MatMire, `ff-` Flexi Factory)
- e.g. `cw-german-shepherd-hatchling`, `mat-hammerhead-shark`

**Model package** (`01_models/`): `<sku>__<CreatorModelName>.zip`

**Sliced file** (`03_ready_to_print/`):
```
<sku>__<ModelName>_<printer>_<material>_<print_time>.gcode[.3mf]
```
- `printer` = `bambu` | `ender` | `ad5x`
- `material` = `pla` | `tpu` | `silk` | `petg`
- ext = `.gcode` (Ender) · `.gcode.3mf` (Bambu, AD5X)
- examples:
  - `cw-classic-crystal-dragon__CrystalDragon_ender_silk_12h57m.gcode`
  - `mat-hammerhead-shark__Hammerhead_ad5x_tpu_7h51m.gcode.3mf`

## Local (DAWES) layout

| Path | Holds |
|---|---|
| `~/print_work/ready/` | the agent's working mirror of `03_ready_to_print/` (rclone target) |
| `~/print_work/*.py` | active senders (`send_bambu.py`, …) |
| `~/Desktop/3d_prints_tests/ad5x_tools/` | AD5X CLI (`ad5x.py`, `ad5x_mc.py`, `ad5x_print.py`) |
| `~/peoples-slicer/` | **the MIT project** — vision + docs + (soon) the unified CLI |
| `~/makerlobster-catalog/` | catalog, `print_flow.py`, `PRINT_RUNBOOK.md`, the YT flow |

## Per-SKU tracking (planned — Notion DB)

One row per licensed SKU, the single source of truth for the business:

| Field | Example |
|---|---|
| SKU / Name / Creator | `cw-german-shepherd-hatchling` / German Shepherd Hatchling / Cinderwing3D |
| License | Patreon (active) |
| File locations | Drive `03_ready_to_print/` link(s), per printer |
| Printer(s) / material | Bambu / PLA-4c · AD5X / TPU |
| Slice settings | colors, time, grams |
| Inventory | on-hand count |
| Prints log | dates / outcomes |
| Sales | price, units sold, revenue |

The more documented we are, the better any agent can operate the Foundry. **Document discipline is
the moat** for "an AI runs the print shop."

## Daily hygiene (the agent's checklist)

1. Empty `00_inbox/` — sort each file into `01_models/`/`02_projects/`.
2. Every file in `03_ready_to_print/` is named correctly + inspected.
3. Finished prints → hero photo into `04_prints/<sku>/`; update the SKU row.
4. Anything ambiguous → ask, don't guess.
