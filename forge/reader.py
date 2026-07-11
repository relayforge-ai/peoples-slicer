"""Read just enough of a g-code file to classify it.

OrcaSlicer splits its metadata: a small HEADER_BLOCK at the top, then a huge
EXECUTABLE_BLOCK, then the CONFIG_BLOCK footer (where `printer_model` lives).
So we read the head + the tail and skip the multi-MB middle.

BambuStudio slices can push CONFIG_BLOCK megabytes past our tail window — when
head+tail misses `printer_model`, we scan the full gcode for classify lines only.

`.gcode.3mf` / `.3mf` jobs store the slice in `Metadata/plate_1.gcode` inside the zip.
"""
import os
import zipfile
from pathlib import Path

from .classifier import JobInfo, classify

HEAD_BYTES = 16_384
TAIL_BYTES = 65_536

_CLASSIFY_PREFIXES = (
    b"; printer_model =",
    b"; printer_settings_id =",
    b"; filament_type =",
    b"; filament_colour =",
    b"; estimated printing time (normal mode)",
    b"; total filament used [g]",
)


def _scan_classify_lines(raw: bytes) -> str:
    """Pull only the header lines the classifier needs from a huge gcode blob."""
    hits: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in _CLASSIFY_PREFIXES):
            hits.append(stripped.decode("utf-8", errors="ignore"))
    return "\n".join(hits)


def _meta_from_raw(raw: bytes) -> str:
    if len(raw) <= HEAD_BYTES + TAIL_BYTES:
        return raw.decode("utf-8", errors="ignore")
    head = raw[:HEAD_BYTES]
    tail = raw[-TAIL_BYTES:]
    return (head + b"\n" + tail).decode("utf-8", errors="ignore")


def _head_tail_plain(path: str) -> bytes:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size <= HEAD_BYTES + TAIL_BYTES:
            return f.read()
        head = f.read(HEAD_BYTES)
        f.seek(-TAIL_BYTES, os.SEEK_END)
        return head + b"\n" + f.read(TAIL_BYTES)


def _full_gcode_bytes(path: str) -> bytes:
    """Return the raw g-code bytes, unzipping `.3mf` / `.gcode.3mf` jobs first.

    A truncated or non-zip `.3mf` (a common casualty of an interrupted LAN copy)
    raises a clear ``ValueError`` naming the file instead of leaking a bare
    ``zipfile.BadZipFile`` stack trace at the import boundary.
    """
    name = Path(path).name
    if Path(path).suffix == ".3mf" or name.endswith(".gcode.3mf"):
        try:
            with zipfile.ZipFile(path) as zf:
                gc_name = next((n for n in zf.namelist() if n.endswith("plate_1.gcode")), None)
                if gc_name is None:
                    raise ValueError(f"no Metadata/plate_1.gcode in {name} — not sliced?")
                return zf.read(gc_name)
        except zipfile.BadZipFile as exc:
            raise ValueError(f"{name} is not a valid .3mf archive (corrupt or incomplete)") from exc
    with open(path, "rb") as f:
        return f.read()


def read_gcode_meta(path: str) -> str:
    """Return head+tail text of a g-code file (whole file if small)."""
    name = Path(path).name
    if Path(path).suffix == ".3mf" or name.endswith(".gcode.3mf"):
        return _meta_from_raw(_full_gcode_bytes(path))
    return _meta_from_raw(_head_tail_plain(path))


def classify_file(path: str) -> JobInfo:
    name = Path(path).name
    is_3mf = Path(path).suffix == ".3mf" or name.endswith(".gcode.3mf")
    raw = _full_gcode_bytes(path) if is_3mf else _head_tail_plain(path)
    meta = _meta_from_raw(raw)
    info = classify(meta)
    if info.printer is None:
        full = raw if is_3mf else _full_gcode_bytes(path)
        extra = _scan_classify_lines(full)
        if extra:
            info = classify(meta + "\n" + extra)
    return info