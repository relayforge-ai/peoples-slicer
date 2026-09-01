"""Builders for magnet 3mfs and in-repo vendor profile trees (REL-602)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

_ASCII_CUBE = (
    "solid c\n facet normal 0 0 1\n  outer loop\n"
    "   vertex 0 0 0\n   vertex 10 0 0\n   vertex 10 10 0\n"
    "  endloop\n endfacet\n"
    " facet normal 0 0 1\n  outer loop\n"
    "   vertex 0 0 0\n   vertex 10 10 0\n   vertex 0 10 0\n"
    "  endloop\n endfacet\nendsolid c\n"
)


def write_ascii_stl(path: Path, *, dx: float = 10, dy: float = 10, dz: float = 8) -> Path:
    path.write_text(
        "solid c\n"
        " facet normal 0 0 1\n  outer loop\n"
        f"   vertex 0 0 0\n   vertex {dx} 0 0\n   vertex {dx} {dy} 0\n"
        "  endloop\n endfacet\n"
        " facet normal 0 0 1\n  outer loop\n"
        f"   vertex 0 0 0\n   vertex {dx} {dy} 0\n   vertex 0 {dy} 0\n"
        "  endloop\n endfacet\n"
        " facet normal 0 0 1\n  outer loop\n"
        f"   vertex 0 0 {dz}\n   vertex {dx} 0 {dz}\n   vertex {dx} {dy} {dz}\n"
        "  endloop\n endfacet\n"
        "endsolid c\n"
    )
    return path


def write_two_plate_magnet_3mf(
    path: Path,
    *,
    captured_name: str = "Captured magnets",
    glue_name: str = "Glue-in",
    captured_object: str = "flexy-pup-captured",
    glue_object: str = "flexy-pup-glue-in",
) -> Path:
    """Minimal Bambu-style project with captured plate 1 and glue-in plate 2."""
    settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="{captured_name}"/>
    <model instance_id="1" object_id="1"/>
  </plate>
  <plate>
    <metadata key="plater_id" value="2"/>
    <metadata key="plater_name" value="{glue_name}"/>
    <model instance_id="2" object_id="2"/>
  </plate>
  <object id="1">
    <metadata key="name" value="{captured_object}"/>
  </object>
  <object id="2">
    <metadata key="name" value="{glue_object}"/>
  </object>
</config>
"""
    model = """<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
          <vertex x="0" y="0" z="0"/>
          <vertex x="20" y="0" z="0"/>
          <vertex x="20" y="20" z="0"/>
          <vertex x="0" y="20" z="0"/>
          <vertex x="0" y="0" z="8"/>
        </vertices>
        <triangles>
          <triangle v1="0" v2="1" v3="2"/>
        </triangles>
      </mesh>
    </object>
  </resources>
  <build><item objectid="1"/></build>
</model>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Metadata/model_settings.config", settings)
        zf.writestr("3D/3dmodel.model", model)
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
    return path


def write_sliced_3mf(
    path: Path,
    *,
    printer_model: str,
    printable_area: list[str],
    extra_settings: dict | None = None,
    gcode_extra: str = "",
) -> Path:
    settings = {
        "printer_model": printer_model,
        "printable_area": printable_area,
        "printable_height": "180",
    }
    if extra_settings:
        settings.update(extra_settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Metadata/project_settings.config", json.dumps(settings))
        zf.writestr(
            "Metadata/plate_1.gcode",
            f"; printer_model = {printer_model}\n{gcode_extra}G28\n",
        )
        zf.writestr(
            "Metadata/slice_info.config",
            '<config><metadata key="prediction" value="600"/><metadata key="weight" value="12"/></config>',
        )
    return path


def _dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_studio_profile_tree(root: Path) -> Path:
    """Minimal inherits chains matching PrinterSpec leaf names."""
    bbl = root / "BBL"
    _dump(
        bbl / "fdm_bbl_3dp_001_common.json",
        {
            "type": "machine",
            "from": "system",
            "name": "fdm_bbl_3dp_001_common",
            "printer_model": "Bambu Lab P1S",
            "printable_area": ["0x0", "256x0", "256x256", "0x256"],
            "nozzle_diameter": ["0.4"],
        },
    )
    _dump(
        bbl / "Bambu Lab A1 mini 0.4 nozzle.json",
        {
            "type": "machine",
            "from": "system",
            "name": "Bambu Lab A1 mini 0.4 nozzle",
            "inherits": "fdm_bbl_3dp_001_common",
            "printer_model": "Bambu Lab A1 mini",
            "printable_area": ["0x0", "180x0", "180x180", "0x180"],
        },
    )
    _dump(
        bbl / "Bambu Lab P1S 0.4 nozzle.json",
        {
            "type": "machine",
            "from": "system",
            "name": "Bambu Lab P1S 0.4 nozzle",
            "inherits": "fdm_bbl_3dp_001_common",
            "printer_model": "Bambu Lab P1S",
            "printable_area": ["0x0", "256x0", "256x256", "0x256"],
        },
    )
    _dump(
        bbl / "fdm_process_common.json",
        {
            "type": "process",
            "from": "system",
            "name": "fdm_process_common",
            "line_width": "0.42",
            "initial_layer_line_width": "0.5",
            "inner_wall_line_width": "0.45",
            "outer_wall_line_width": "0.42",
            "enable_prime_tower": "0",
        },
    )
    _dump(
        bbl / "0.20mm Standard @BBL A1M.json",
        {
            "type": "process",
            "from": "system",
            "name": "0.20mm Standard @BBL A1M",
            "inherits": "fdm_process_common",
            "layer_height": "0.2",
        },
    )
    _dump(
        bbl / "0.20mm Standard @BBL P1S.json",
        {
            "type": "process",
            "from": "system",
            "name": "0.20mm Standard @BBL P1S",
            "inherits": "fdm_process_common",
            "layer_height": "0.2",
        },
    )
    _dump(
        bbl / "Bambu PLA Basic @BBL A1M.json",
        {
            "type": "filament",
            "from": "system",
            "name": "Bambu PLA Basic @BBL A1M",
            "filament_type": ["PLA"],
        },
    )
    _dump(
        bbl / "Bambu PLA Basic @BBL P1S.json",
        {
            "type": "filament",
            "from": "system",
            "name": "Bambu PLA Basic @BBL P1S",
            "filament_type": ["PLA"],
        },
    )

    ff = root / "Flashforge"
    _dump(
        ff / "fdm_flashforge_common.json",
        {
            "type": "machine",
            "from": "system",
            "name": "fdm_flashforge_common",
            "printer_model": "Flashforge AD5X",
            "printable_area": ["0x0", "220x0", "220x220", "0x220"],
        },
    )
    _dump(
        ff / "Flashforge AD5X 0.4 nozzle.json",
        {
            "type": "machine",
            "from": "system",
            "name": "Flashforge AD5X 0.4 nozzle",
            "inherits": "fdm_flashforge_common",
            "printer_model": "Flashforge AD5X",
            "printable_area": ["0x0", "220x0", "220x220", "0x220"],
        },
    )
    _dump(
        ff / "fdm_process_common.json",
        {
            "type": "process",
            "from": "system",
            "name": "fdm_process_common",
            "line_width": "0.42",
            "initial_layer_line_width": "0.5",
            "inner_wall_line_width": "0.45",
            "outer_wall_line_width": "0.42",
        },
    )
    _dump(
        ff / "0.20mm Standard @FF AD5X.json",
        {
            "type": "process",
            "from": "system",
            "name": "0.20mm Standard @FF AD5X",
            "inherits": "fdm_process_common",
            "layer_height": "0.2",
        },
    )
    _dump(
        ff / "Flashforge PLA Basic.json",
        {
            "type": "filament",
            "from": "system",
            "name": "Flashforge PLA Basic",
            "filament_type": ["PLA"],
        },
    )

    foundry = root / "Foundry"
    _dump(
        foundry / "Ender3_Klipper.json",
        {
            "type": "machine",
            "from": "system",
            "name": "Ender3 Klipper (Foundry)",
            "printer_model": "Ender3 Klipper (Foundry)",
            "printable_area": ["0x0", "235x0", "235x235", "0x235"],
        },
    )
    _dump(
        foundry / "Foundry_Process_0.20.json",
        {
            "type": "process",
            "from": "system",
            "name": "Foundry 0.20mm Brim",
            "line_width": "0.42",
            "initial_layer_line_width": "0.42",
            "inner_wall_line_width": "0.42",
            "outer_wall_line_width": "0.42",
        },
    )
    _dump(
        foundry / "Silk_PLA.json",
        {
            "type": "filament",
            "from": "system",
            "name": "Silk PLA (Foundry)",
            "filament_type": ["PLA"],
        },
    )
    return root


def write_kobra_flexypup_3mf(path: Path) -> Path:
    """Printverse Kobra Max origin of fill-20260901-a1mini-flexypup.

    5 colours, 400 mm bed, prime tower off, wipe_tower_y=220 — plus captured
    + glue-in plates. This is the file class that leaked through --load-settings.
    """
    settings = {
        "printer_model": "Anycubic Kobra 3 Max",
        "printer_settings_id": "Anycubic Kobra 3 Max 0.4 nozzle",
        "print_settings_id": "0.20mm Standard @Kobra3Max",
        "printable_area": ["0x0", "400x0", "400x400", "0x400"],
        "printable_height": "400",
        "enable_prime_tower": "0",
        "wipe_tower_x": "220",
        "wipe_tower_y": "220",
        "prime_tower_width": "35",
        "filament_colour": "#80FF80;#FFFFFF;#0000FF;#6F5034;#FFFF00",
    }
    # Reuse the two-plate magnet mesh/settings, then inject Kobra project_settings.
    write_two_plate_magnet_3mf(path)
    tmp = path.with_suffix(".tmp.3mf")
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            zout.writestr(info, zin.read(info.filename))
        zout.writestr(
            "Metadata/project_settings.config",
            json.dumps(settings, indent=2) + "\n",
        )
    tmp.replace(path)
    return path


ASCII_CUBE = _ASCII_CUBE
