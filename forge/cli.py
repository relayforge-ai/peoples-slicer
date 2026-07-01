"""The `forge` command — argparse, zero third-party deps (mom-simple, Windows-safe)."""
from __future__ import annotations

import argparse

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
    sub = parser.add_subparsers(dest="command", metavar="{" + ",".join(SUBCOMMANDS) + "}")
    for name, help_text in (
        ("discover", "find and connect printers on the LAN (enter a code once)"),
        ("review", "audit a sliced file's finicky parameters for a printer/material"),
        ("send", "send a sliced file to a printer, headless, zero parameter loss"),
        ("status", "show what is queued and printing"),
        ("watch", "watch a drop folder and route jobs automatically"),
    ):
        sub.add_parser(name, help=help_text)
    return parser


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
    # Subcommands are stubbed in Phase 0; the engine lands in Plans 1–2.
    print(f"`forge {args.command}` is not implemented yet — see docs/superpowers/plans/.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
