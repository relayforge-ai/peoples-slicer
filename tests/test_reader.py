from forge.reader import classify_file


def _write_realistic_gcode(tmp_path):
    """Mimic OrcaSlicer layout: tiny HEADER_BLOCK on top, huge executable middle,
    and the CONFIG_BLOCK (with printer_model) only at the very end."""
    lines = [
        "; HEADER_BLOCK_START",
        "; total layer number: 20",
        "; filament: 1",
        "; HEADER_BLOCK_END",
        "; EXECUTABLE_BLOCK_START",
    ]
    lines += [f"G1 X{i % 200} Y{(i * 3) % 200} E{i * 0.01:.3f}" for i in range(40000)]
    lines += [
        "; EXECUTABLE_BLOCK_END",
        "; total filament used [g] = 33.53",
        "; CONFIG_BLOCK_START",
        "; filament_colour = #F72224",
        "; filament_type = TPU",
        "; printer_model = Flashforge AD5X",
        "; CONFIG_BLOCK_END",
    ]
    p = tmp_path / "sample.gcode"
    p.write_text("\n".join(lines) + "\n")
    return str(p)


def test_classify_file_reads_footer_config(tmp_path):
    info = classify_file(_write_realistic_gcode(tmp_path))
    assert info.printer == "ad5x"
    assert info.material == "TPU"
    assert info.colors == 1
    assert info.est_grams == 33.53
