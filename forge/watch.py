"""Watch a drop folder and route new sliced files through the dispatcher."""
from __future__ import annotations

import os
import time
from pathlib import Path

WATCH_EXTENSIONS = (".gcode", ".3mf")
_POLL_DEFAULT = float(os.environ.get("FORGE_WATCH_INTERVAL", "5"))


def is_watchable(path: str) -> bool:
    name = path.lower()
    if name.endswith(".gcode.3mf"):
        return True
    return any(name.endswith(ext) for ext in WATCH_EXTENSIONS)


def collect_new_files(watch_dir: str, seen: set[str]) -> list[str]:
    root = Path(watch_dir)
    if not root.is_dir():
        return []
    new: list[str] = []
    for entry in sorted(root.rglob("*")):
        if not entry.is_file():
            continue
        path = str(entry.resolve())
        if not is_watchable(path):
            continue
        if path not in seen:
            seen.add(path)
            new.append(path)
    return new


def watch_once(
    watch_dir: str,
    dispatcher,
    *,
    seen: set[str] | None = None,
    bed_confirmed: bool | None = None,
) -> list[dict]:
    seen_set = seen if seen is not None else set()
    results: list[dict] = []
    for path in collect_new_files(watch_dir, seen_set):
        extra = {}
        if bed_confirmed is not None:
            extra["bed_confirmed_clear"] = bed_confirmed
        results.append(dispatcher.submit(path, **extra))
    return results


def watch_loop(
    watch_dir: str,
    dispatcher,
    *,
    interval: float = _POLL_DEFAULT,
    bed_confirmed: bool | None = None,
    sleep_fn=time.sleep,
) -> None:
    seen: set[str] = set()
    while True:
        watch_once(watch_dir, dispatcher, seen=seen, bed_confirmed=bed_confirmed)
        dispatcher.drain()
        sleep_fn(interval)


def default_watch_dir() -> str:
    return os.path.expanduser(os.environ.get("FORGE_WATCH_DIR", "~/forge-drop"))