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

    disc_p = sub.add_parser("discover", help="find and connect printers on the LAN (enter a code once)")
    disc_p.add_argument("--subnet", help="CIDR to scan (default: FORGE_DISCOVER_SUBNET or 192.168.4.0/24)")
    disc_p.add_argument("--host", action="append", dest="hosts", help="probe specific host(s) instead of scanning")
    disc_p.add_argument("--save", metavar="KEY", help="save a discovered printer into FORGE_CONFIG under KEY")

    rev_p = sub.add_parser("review", help="audit a sliced file's finicky parameters for a printer/material")
    rev_p.add_argument("file", help="path to .gcode or .gcode.3mf")
    rev_p.add_argument("--printer", help="override classified printer key for the profile rules")

    send_p = sub.add_parser("send", help="send a sliced file to a printer, headless, zero parameter loss")
    send_p.add_argument("file", help="path to .gcode or .gcode.3mf")
    send_p.add_argument("--dry-run", action="store_true", help="classify and review only, do not send")
    send_p.add_argument(
        "--bed-confirmed",
        action="store_true",
        help="confirm the bed is clear (required before send)",
    )

    sub.add_parser("status", help="show what is queued and printing")
    watch_p = sub.add_parser("watch", help="watch a drop folder and route jobs automatically")
    watch_p.add_argument("--dir", dest="watch_dir", help="folder to watch (default: FORGE_WATCH_DIR or ~/forge-drop)")
    watch_p.add_argument("--once", action="store_true", help="process existing files once and exit")
    watch_p.add_argument(
        "--bed-confirmed",
        action="store_true",
        help="confirm beds are clear before auto-sending (required for sends)",
    )
    watch_p.add_argument("--interval", type=float, default=None, help="poll interval seconds (default: 5)")
    return parser


def _default_queue_path() -> str:
    return os.path.expanduser(os.environ.get("FORGE_QUEUE_PATH", "~/.forge_queue.json"))


def _default_events_path() -> str:
    return os.path.expanduser(os.environ.get("FORGE_EVENTS_PATH", "~/.forge_jobs.jsonl"))


def _input_file_error(path: str) -> str | None:
    """Return a one-line error if ``path`` is not a readable file, else ``None``.

    Guards the ``send`` / ``review`` commands, whose file argument is handed
    straight to the classifier (``os.path.getsize`` / ``zipfile.ZipFile``). A
    mistyped or missing path — the mistake a non-technical, headless operator
    makes most — otherwise leaks a bare ``FileNotFoundError`` traceback instead
    of the clear, actionable line the north star asks for.
    """
    if not os.path.isfile(path):
        return f"file not found: {path}"
    return None


def cmd_send(args, config_path: str | None) -> int:
    from .config import build_adapters, load_config
    from .dispatcher import Dispatcher
    from .guardian import Guardian
    from .jobqueue import JobQueue
    from .reader import classify_file
    from .store import JsonlStore, NullStore

    err = _input_file_error(args.file)
    if err:
        print(err, file=sys.stderr)
        return 1

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


def cmd_discover(args, config_path: str | None) -> int:
    from .discover import (
        default_subnet,
        iter_subnet_hosts,
        merge_into_config,
        printer_config_entry,
        probe_host,
        scan_hosts,
        to_json,
    )

    if args.hosts:
        found = scan_hosts(args.hosts, prober=probe_host)
    else:
        subnet = args.subnet or default_subnet()
        # Validate the CIDR at the boundary: a mistyped --subnet (or a bad
        # FORGE_DISCOVER_SUBNET) otherwise leaks a bare ipaddress ValueError
        # traceback instead of one actionable line, the same landmine that
        # `_input_file_error` files down for send/review.
        try:
            hosts = iter_subnet_hosts(subnet)
        except ValueError:
            print(
                f"invalid --subnet {subnet!r}: expected a CIDR like 192.168.4.0/24",
                file=sys.stderr,
            )
            return 1
        found = scan_hosts(hosts, prober=probe_host)

    print(to_json(found))
    if args.save:
        if len(found) != 1:
            print(
                f"--save requires exactly one discovered printer; found {len(found)}.",
                file=sys.stderr,
            )
            return 1
        entry = printer_config_entry(found[0])
        merge_into_config(args.save, entry, config_path)
        print(f"saved printer '{args.save}' to config")
    return 0


def cmd_review(args, config_path: str | None) -> int:
    from .review import review_file

    err = _input_file_error(args.file)
    if err:
        print(err, file=sys.stderr)
        return 1

    report = review_file(args.file, printer=args.printer)
    print(json.dumps(report, indent=2))
    return 1 if report.get("blocking") else 0


def cmd_watch(args, config_path: str | None) -> int:
    from .config import build_adapters, load_config
    from .dispatcher import Dispatcher
    from .guardian import Guardian
    from .jobqueue import JobQueue
    from .store import JsonlStore
    from .watch import default_watch_dir, watch_loop, watch_once

    cfg = load_config(config_path)
    adapters = build_adapters(cfg)
    if not adapters:
        print("No printers configured. Run `forge discover` or set FORGE_CONFIG.", file=sys.stderr)
        return 1

    watch_dir = args.watch_dir or default_watch_dir()
    os.makedirs(watch_dir, exist_ok=True)

    store = JsonlStore(_default_events_path())
    queue = JobQueue(_default_queue_path())
    guardian = Guardian()
    dispatcher = Dispatcher(adapters=adapters, queue=queue, store=store, guardian=guardian)
    bed = True if args.bed_confirmed else None

    if args.once:
        results = watch_once(watch_dir, dispatcher, bed_confirmed=bed)
        print(json.dumps(results, indent=2))
        dispatcher.drain()
        return 0

    print(f"watching {watch_dir} (Ctrl+C to stop)")
    try:
        watch_loop(
            watch_dir,
            dispatcher,
            interval=args.interval or float(os.environ.get("FORGE_WATCH_INTERVAL", "5")),
            bed_confirmed=bed,
        )
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


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
    if args.command == "discover":
        return cmd_discover(args, config_path)
    if args.command == "review":
        return cmd_review(args, config_path)
    if args.command == "send":
        return cmd_send(args, config_path)
    if args.command == "status":
        return cmd_status(args, config_path)
    if args.command == "watch":
        return cmd_watch(args, config_path)

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())