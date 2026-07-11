# The 30-second demo (for the README + launch post)

A CLI tool lives or dies on one asciicast. This is the storyboard. Record it with
[`vhs`](https://github.com/charmbracelet/vhs) (scriptable, deterministic GIF) or `asciinema`.

## The money shot
The **AD5X headless multicolor send** — the thing even Orca-Flashforge only does through a manual GUI
dialog. Show a real multicolor part going from a sliced file to a moving printer with **one command**,
the IFS slot map auto-built. That single moment *is* the pitch ("the GUI hides it; the CLI made it
bulletproof").

## Storyboard (≈30s, real printer — highest credibility)
```bash
# a laptop, a sliced multicolor file, a printer on the LAN
forge discover                       # → finds the AD5X, one line, "connected"
forge review lobster_4c.gcode.3mf    # → ✅ green: params intact, 4 tools → 4 IFS slots
forge send lobster_4c.gcode.3mf      # → uploads, auto-builds materialMappings, START
forge status                         # → "printing · lobster_4c · tool 1/4" — cut to the nozzle moving
```
End on the print head laying the first color. Caption: *"Sliced anywhere. Sent headless. Zero
parameters lost."*

## Hardware-free version (for CI / contributors who have no printer)
Run the same script against a mock adapter (see `tests/` fixtures + `forge/fixtures.py`) so the GIF
records identically without a machine on the LAN. Use this for the repo's animated README; keep the
**real** one for the launch post (Reddit r/3Dprinting, HN, the Notion page) — real hardware is the
credibility.

## Recording notes
- `vhs demo.tape` → `demo.gif`; keep it < 3 MB, ≤ 12s loop for the README top-fold.
- Show `forge --help` for one beat so viewers see the whole surface (`discover/review/send/status/watch`).
- Do **not** show real `AD5X_CHECKCODE` / `BAMBU_ACCESS_CODE` on screen — export them before recording.
