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
