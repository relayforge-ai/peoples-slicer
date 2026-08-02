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
    """Route every not-yet-seen file in ``watch_dir`` through the dispatcher once.

    Returns one result dict per newly-seen file. A file that raises while being
    classified or routed (e.g. a corrupt / half-copied ``.3mf`` from an
    interrupted LAN transfer, or a file that vanished mid-copy) is turned into an
    ``{"state": "errored", ...}`` result instead of propagating — a single bad
    drop must never kill the headless :func:`watch_loop` and stall every good
    file queued behind it. The offending path is already marked seen by
    :func:`collect_new_files`, so it is reported once and not retried each tick.
    """
    seen_set = seen if seen is not None else set()
    results: list[dict] = []
    for path in collect_new_files(watch_dir, seen_set):
        extra = {}
        if bed_confirmed is not None:
            extra["bed_confirmed_clear"] = bed_confirmed
        try:
            results.append(dispatcher.submit(path, **extra))
        except Exception as exc:  # noqa: BLE001 - one bad drop must not kill the daemon
            results.append(
                {
                    "state": "errored",
                    "name": os.path.basename(path),
                    "path": path,
                    "reason": str(exc),
                }
            )
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