"""Read just enough of a g-code file to classify it.

OrcaSlicer splits its metadata: a small HEADER_BLOCK at the top, then a huge
EXECUTABLE_BLOCK, then the CONFIG_BLOCK footer (where `printer_model` lives).
So we read the head + the tail and skip the multi-MB middle.

`.gcode.3mf` / `.3mf` jobs store the slice in `Metadata/plate_1.gcode` inside the zip.
"""
import os
import zipfile
from pathlib import Path

from .classifier import JobInfo, classify

HEAD_BYTES = 16_384
TAIL_BYTES = 65_536


def _read_plain_gcode(path: str) -> str:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size <= HEAD_BYTES + TAIL_BYTES:
            data = f.read()
        else:
            head = f.read(HEAD_BYTES)
            f.seek(-TAIL_BYTES, os.SEEK_END)
            data = head + b"\n" + f.read(TAIL_BYTES)
    return data.decode("utf-8", errors="ignore")


def read_gcode_meta(path: str) -> str:
    """Return head+tail text of a g-code file (whole file if small)."""
    name = Path(path).name
    if Path(path).suffix == ".3mf" or name.endswith(".gcode.3mf"):
        with zipfile.ZipFile(path) as zf:
            gc_name = next((n for n in zf.namelist() if n.endswith("plate_1.gcode")), None)
            if gc_name is None:
                raise ValueError(f"no Metadata/plate_1.gcode in {name} — not sliced?")
            raw = zf.read(gc_name)
            if len(raw) <= HEAD_BYTES + TAIL_BYTES:
                return raw.decode("utf-8", errors="ignore")
            head = raw[:HEAD_BYTES]
            tail = raw[-TAIL_BYTES:]
            return (head + b"\n" + tail).decode("utf-8", errors="ignore")
    return _read_plain_gcode(path)


def classify_file(path: str) -> JobInfo:
    return classify(read_gcode_meta(path))
