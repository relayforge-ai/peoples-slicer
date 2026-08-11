"""The `forge` command — argparse, zero third-party deps for the CLI itself."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import BRAND, __version__

SUBCOMMANDS = (
    "discover", "review", "send", "status", "watch",
    "slice", "slice-send", "slice-batch", "harvest",
    "gui",
)


def banner() -> str:
    return (
        f"{BRAND['product']} v{__version__} — {BRAND['tagline']}\n"
        f"MIT open source · CLI {BRAND['cli']} · {BRAND['home_url']}"
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

    # REL-600 / REL-601 — headless multi-printer slice (+ optional send)
    slice_p = sub.add_parser(
        "slice",
        help="REL-600/601: headless-slice a model for a studio printer (fit + flattened profiles)",
    )
    slice_p.add_argument("model", help="path to .stl / .3mf")
    slice_p.add_argument(
        "--printer",
        required=True,
        choices=("a1mini", "a2l", "ad5x", "ender"),
        help="target printer key (forge_printers / routing table)",
    )
    slice_p.add_argument("-o", "--output", help="output .gcode / .gcode.3mf path")
    slice_p.add_argument("--dry-run", action="store_true", help="resolve profiles + fit only")
    slice_p.add_argument("--auto-refit", action="store_true", help="scale part to fit bed (REL-600)")
    slice_p.add_argument(
        "--goal",
        choices=("single", "photo_line", "max_parts", "estimate"),
        help="plate policy goal (sets scale/repetitions/arrange)",
    )
    slice_p.add_argument("--plan-only", action="store_true", help="print plate policy JSON and exit")
    slice_p.add_argument("--timeout", type=int, default=900)

    ss_p = sub.add_parser(
        "slice-send",
        help="REL-601: slice then send (guardian + --bed-confirmed required for live send)",
    )
    ss_p.add_argument("model", help="path to .stl / .3mf")
    ss_p.add_argument("--printer", required=True, choices=("a1mini", "a2l", "ad5x", "ender"))
    ss_p.add_argument("-o", "--output", help="sliced output path")
    ss_p.add_argument("--auto-refit", action="store_true")
    ss_p.add_argument("--goal", choices=("single", "photo_line", "max_parts", "estimate"))
    ss_p.add_argument("--timeout", type=int, default=900)
    ss_p.add_argument("--dry-run", action="store_true", help="slice + classify only, do not send")
    ss_p.add_argument(
        "--bed-confirmed",
        action="store_true",
        help="confirm bed clear (required for live send; fail-closed otherwise)",
    )

    sub.add_parser("harvest", help="REL-600: harvest Orca/Bambu vendor profiles into ~/.forge/harvest")

    batch_p = sub.add_parser(
        "slice-batch",
        help="REL-599: A1 mini multi-plate batch (≤4) for PlateCycler photo line",
    )
    batch_p.add_argument("models", nargs="+", help="model paths (.stl/.3mf), max 4 per batch")
    batch_p.add_argument("-o", "--out-dir", help="output directory for plate_*.gcode.3mf")
    batch_p.add_argument("--auto-refit", action="store_true", default=True)
    batch_p.add_argument("--no-auto-refit", action="store_true")
    batch_p.add_argument("--dry-run", action="store_true")
    batch_p.add_argument("--timeout", type=int, default=900)

    gui_p = sub.add_parser(
        "gui",
        help="open the local Studio UI (localhost only — humans without agents)",
    )
    gui_p.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    gui_p.add_argument("--host", default="127.0.0.1", help="bind address (localhost only)")
    gui_p.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
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
    import time
    from dataclasses import asdict

    from .discover import (
        default_subnet,
        iter_subnet_hosts,
        merge_into_config,
        printer_config_entry,
        probe_host,
        scan_hosts,
        to_json,
    )

    # Stream, don't buffer: a sequential /24 scan could be silently slow (up to ~19 min
    # worst case at the default per-probe timeout) with nothing printed until the very
    # end — indistinguishable from a hang. Print each hit the instant it's found, and a
    # throttled progress line to stderr so a scan that's finding nothing still shows
    # it's alive.
    last_progress = 0.0

    def _on_result(found_printer):
        print(json.dumps(asdict(found_printer)))

    def _on_progress(done: int, total: int) -> None:
        nonlocal last_progress
        now = time.monotonic()
        if done == total or now - last_progress >= 1.0:
            print(f"scanned {done}/{total}...", file=sys.stderr)
            last_progress = now

    if args.hosts:
        found = scan_hosts(
            args.hosts, prober=probe_host, on_result=_on_result, on_progress=_on_progress
        )
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
        found = scan_hosts(
            hosts, prober=probe_host, on_result=_on_result, on_progress=_on_progress
        )

    print(f"--- {len(found)} found ---", file=sys.stderr)
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


def cmd_gui(args, config_path: str | None) -> int:
    """Local Studio UI for humans — same slice/review/send path as the CLI."""
    from .gui_server import serve

    try:
        serve(
            host=args.host,
            port=int(args.port),
            config_path=config_path,
            open_browser=not args.no_browser,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR: could not bind Studio — {e}", file=sys.stderr)
        return 1
    return 0


def cmd_slice(args, config_path: str | None) -> int:
    """REL-600/601: headless multi-printer slice."""
    from .slice import FitError, SliceError, plan_plate, refit_scale, slice_for
    from .slice.printers import get_printer

    if args.plan_only:
        policy = plan_plate(args.model, args.printer, goal=args.goal or "single")
        refit = refit_scale(args.model, args.printer)
        print(json.dumps({
            "refit": {
                "scale": refit.scale,
                "fits_without_scale": refit.fits_without_scale,
                "note": refit.note,
            },
            "policy": policy.as_dict(),
            "printer": get_printer(args.printer).display_name,
        }, indent=2))
        return 0

    try:
        result = slice_for(
            args.model,
            args.printer,
            output=args.output,
            timeout=args.timeout,
            dry_run=args.dry_run,
            auto_refit=args.auto_refit or (args.goal is not None),
            goal=args.goal,
        )
    except FitError as e:
        print(f"FIT: {e}", file=sys.stderr)
        return 3
    except (SliceError, FileNotFoundError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(json.dumps({
        "ok": result.ok,
        "printer": result.printer,
        "backend": result.backend,
        "output": result.output,
        "bounds": result.bounds,
        "estimates": result.estimates,
        "scale": result.scale,
        "repetitions": result.repetitions,
        "policy": result.policy,
        "detail": result.detail,
    }, indent=2))
    return 0


def cmd_slice_send(args, config_path: str | None) -> int:
    """REL-601: slice → review classify → guardian-gated send."""
    from .slice import FitError, SliceError, slice_for

    # 1) Slice
    try:
        result = slice_for(
            args.model,
            args.printer,
            output=args.output,
            timeout=args.timeout,
            dry_run=False,
            auto_refit=args.auto_refit or (args.goal is not None),
            goal=args.goal,
        )
    except FitError as e:
        print(f"FIT: {e}", file=sys.stderr)
        return 3
    except (SliceError, FileNotFoundError, KeyError) as e:
        print(f"SLICE ERROR: {e}", file=sys.stderr)
        return 1

    print(json.dumps({
        "sliced": True,
        "output": result.output,
        "estimates": result.estimates,
        "scale": result.scale,
    }, indent=2))

    # 2) Send path reuses cmd_send logic
    class _SendArgs:
        file = result.output
        dry_run = True if args.dry_run else False
        bed_confirmed = bool(args.bed_confirmed)

    if args.dry_run:
        print("(slice-send dry-run — not sending; pass without --dry-run and with --bed-confirmed to send)")
        # still classify
        from .reader import classify_file
        info = classify_file(result.output)
        print(json.dumps({
            "printer": info.printer,
            "material": info.material,
            "colors": info.colors,
            "est_seconds": info.est_seconds,
            "est_grams": info.est_grams,
        }, indent=2))
        return 0

    return cmd_send(_SendArgs(), config_path)


def cmd_slice_batch(args, config_path: str | None) -> int:
    """REL-599: multi-plate a1mini batch for PlateCycler."""
    from .slice import slice_batch

    auto = not bool(getattr(args, "no_auto_refit", False))
    result = slice_batch(
        list(args.models),
        out_dir=args.out_dir,
        auto_refit=auto,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    print(json.dumps(result.as_dict(), indent=2))
    ok = all(p.get("status") in {"ok", "planned"} for p in result.plates) if result.plates else False
    return 0 if ok or args.dry_run else 1


def cmd_harvest(args, config_path: str | None) -> int:
    """REL-600: harvest installed Orca/Bambu profile trees."""
    from .slice.profile_harvester import (
        DEFAULT_MANIFEST,
        diff_manifests,
        harvest_all,
        load_manifest,
        write_manifest,
    )

    new = harvest_all()
    old = load_manifest(DEFAULT_MANIFEST)
    path = write_manifest(new, DEFAULT_MANIFEST)
    diff = diff_manifests(old or {"records": []}, new)
    print(json.dumps({
        "count": new["count"],
        "vendors": len(new.get("vendors") or []),
        "types": new.get("types"),
        "manifest": str(path),
        "diff": {
            "added": diff.get("added_count"),
            "changed": diff.get("changed_count"),
            "removed": diff.get("removed_count"),
        },
    }, indent=2))
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
    if args.command == "slice":
        return cmd_slice(args, config_path)
    if args.command == "slice-send":
        return cmd_slice_send(args, config_path)
    if args.command == "harvest":
        return cmd_harvest(args, config_path)
    if args.command == "slice-batch":
        return cmd_slice_batch(args, config_path)
    if args.command == "gui":
        return cmd_gui(args, config_path)

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())