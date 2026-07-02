"""Read just enough of a g-code file to classify it.

OrcaSlicer splits its metadata: a small HEADER_BLOCK at the top, then a huge
EXECUTABLE_BLOCK, then the CONFIG_BLOCK footer (where `printer_model` lives).
So we read the head + the tail and skip the multi-MB middle.
"""
import os

from .classifier import JobInfo, classify

HEAD_BYTES = 16_384
TAIL_BYTES = 65_536


def read_gcode_meta(path: str) -> str:
    """Return head+tail text of a g-code file (whole file if small)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size <= HEAD_BYTES + TAIL_BYTES:
            data = f.read()
        else:
            head = f.read(HEAD_BYTES)
            f.seek(-TAIL_BYTES, os.SEEK_END)
            data = head + b"\n" + f.read(TAIL_BYTES)
    return data.decode("utf-8", errors="ignore")


def classify_file(path: str) -> JobInfo:
    return classify(read_gcode_meta(path))
