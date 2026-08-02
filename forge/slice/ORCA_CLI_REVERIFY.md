# OrcaSlicer CLI re-verify (DAWES) — REL-599

**Date:** 2026-08-01  
**Prior report:** return -24 (AD5X/Ender slicing lived on Tycho)

## Result: PASS

```text
ORCA=/home/ryan-sheldon/orcaslicer/squashfs-root
LD_LIBRARY_PATH=$(find $ORCA -name '*.so*' …)
xvfb-run -a $ORCA/bin/orca-slicer test_cube.stl \
  --load-settings "Flashforge AD5X 0.4 nozzle.json;0.20mm Standard @FF AD5X.json" \
  --load-filaments "Flashforge PLA Basic.json" \
  --arrange 1 --orient 1 --slice 0 --outputdir /tmp/orca-ad5x.XXX
```

- **exit code:** 0  
- **output:** `plate_1.gcode` (~412 KB)  
- **binary:** OrcaSlicer-2.3.2 extracted AppImage (`~/orcaslicer/squashfs-root/bin/orca-slicer`)

AD5X is no longer blocked on DAWES for headless CLI. Ender continues via Foundry profiles + `slice-ender.sh` / `slice_for(..., "ender")`.
