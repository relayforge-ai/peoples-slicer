"""The `forge` command — argparse, zero third-party deps for the CLI itself."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import BRAND, __version__

SUBCOMMANDS = ("discover", "review", "send", "status", "watch")


def banner() -> str:
    return (
        f"{BRAND['product']} v{__version__} — {BRAND['tagline']}\n"
        f"Part of {BRAND['umbrella']} · made in the Telchar studio "
        f"→ {BRAND['home_url']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge",
        description=banner(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"forge {__version__}")
    parser.add_argument(
        "--config",
        help="path to forge config JSON (or set FORGE_CONFIG)",
    )
    sub = parser.add_subparsers(dest="command", metavar="{" + ",".join(SUBCOMMANDS) + "}")

    sub.add_parser("discover", help="find and connect printers on the LAN (enter a code once)")
    sub.add_parser("review", help="audit a sliced file's finicky parameters for a printer/material")

    send_p = sub.add_parser("send", help="send a sliced file to a printer, headless, zero parameter loss")
    send_p.add_argument("file", help="path to .gcode or .gcode.3mf")
    send_p.add_argument("--dry-run", action="store_true", help="classify and review only, do not send")
    send_p.add_argument(
        "--bed-confirmed",
        action="store_true",
        help="confirm the bed is clear (required before send)",
    )

    sub.add_parser("status", help="show what is queued and printing")
    sub.add_parser("watch", help="watch a drop folder and route jobs automatically")
    return parser


def _default_queue_path() -> str:
    return os.path.expanduser(os.environ.get("FORGE_QUEUE_PATH", "~/.forge_queue.json"))


def _default_events_path() -> str:
    return os.path.expanduser(os.environ.get("FORGE_EVENTS_PATH", "~/.forge_jobs.jsonl"))


def cmd_send(args, config_path: str | None) -> int:
    from .config import build_adapters, load_config
    from .dispatcher import Dispatcher
    from .guardian import Guardian
    from .jobqueue import JobQueue
    from .reader import classify_file
    from .store import JsonlStore, NullStore

    info = classify_file(args.file)
    print(json.dumps({
        "printer": info.printer,
        "material": info.material,
        "colors": info.colors,
        "est_seconds": info.est_seconds,
        "est_grams": info.est_grams,
    }, indent=2))

    if args.dry_run:
        print("(dry-run — not sending)")
        return 0

    cfg = load_config(config_path)
    adapters = build_adapters(cfg)
    if not adapters:
        print("No printers configured. Set FORGE_CONFIG or AD5X_HOST / BAMBU_HOST / MOONRAKER_URL.", file=sys.stderr)
        return 1

    store = NullStore() if args.dry_run else JsonlStore(_default_events_path())
    queue = JobQueue(_default_queue_path())
    guardian = Guardian()
    dispatcher = Dispatcher(adapters=adapters, queue=queue, store=store, guardian=guardian)

    result = dispatcher.submit(
        args.file,
        bed_confirmed_clear=args.bed_confirmed,
    )
    if result.get("state") == "vetoed" and "bed" in result.get("reason", ""):
        print(f"VETOED: {result['reason']}. Pass --bed-confirmed after checking the camera.", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result.get("state") in ("printing", "queued") else 1


def cmd_status(args, config_path: str | None) -> int:
    from .config import build_adapters, load_config
    from .jobqueue import JobQueue

    cfg = load_config(config_path)
    adapters = build_adapters(cfg)
    queue = JobQueue(_default_queue_path())

    snapshot = {
        "printers": {
            key: {
                "status": adapter.status(),
                "active": queue.active(key),
                "pending": queue.pending(key),
            }
            for key, adapter in adapters.items()
        }
    }
    print(json.dumps(snapshot, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0

    if not getattr(args, "command", None):
        print(banner())
        print("\nRun `forge --help` for commands.")
        return 0

    config_path = getattr(args, "config", None)
    if args.command == "send":
        return cmd_send(args, config_path)
    if args.command == "status":
        return cmd_status(args, config_path)

    print(f"`forge {args.command}` is not implemented yet — see docs/superpowers/plans/.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())