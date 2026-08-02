# A1 mini Chitu PlateCycler C1M — verified plate_change_gcode

Place the **on-hardware verified** inter-plate gcode at:

```text
a1mini_chitu_c1m.gcode
```

## Rules

1. This is **`plate_change_gcode` between plates of a multi-plate job**, not `machine_end_gcode`.
2. Reference: OrcaSlicer PR [#13177](https://github.com/SoftFever/OrcaSlicer/pull/13177).
3. Cap batches at **4 plates** (feeder capacity).
4. **Do not invent** coordinates or eject moves — Ryan verifies the first cycle attended.
5. Skip plate-change on cancel/fail so a half-print is never shoved into the bin.
6. Webcam bed-empty check remains the evidence for `bed_confirmed_clear`, not the feeder alone.

Until this file exists, `load_plate_change_gcode()` raises `PlateChangeNotConfigured`.
