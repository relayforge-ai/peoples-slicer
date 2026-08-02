#!/usr/bin/env python3
"""CLI: harvest Orca/Bambu profiles and diff against last manifest (REL-600)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# forge/slice/scripts → repo root (parents[3]) so `import forge` works
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from forge.slice.profile_harvester import (  # noqa: E402
    DEFAULT_MANIFEST,
    diff_manifests,
    harvest_all,
    load_manifest,
    write_manifest,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="REL-600 profile harvester")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--diff-only", action="store_true", help="diff without writing")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args(argv)

    new = harvest_all()
    old = load_manifest(args.out)
    diff = diff_manifests(old or {"records": []}, new) if old or args.diff_only else {
        "added": [], "removed": [], "changed": [],
        "added_count": new["count"], "removed_count": 0, "changed_count": 0,
        "first_harvest": True,
    }

    if not args.diff_only:
        write_manifest(new, args.out)
        # also write a small latest-diff for cron logs
        diff_path = args.out.with_name("profile_diff_latest.json")
        diff_path.write_text(json.dumps(diff, indent=2) + "\n")

    summary = {
        "count": new["count"],
        "vendors": len(new.get("vendors") or []),
        "types": new.get("types"),
        "manifest": str(args.out),
        "diff": diff,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"harvested {new['count']} profiles from {len(new.get('vendors') or [])} vendors")
        print(f"  types: {new.get('types')}")
        print(f"  manifest: {args.out}")
        print(
            f"  diff: +{diff.get('added_count', 0)} "
            f"~{diff.get('changed_count', 0)} "
            f"-{diff.get('removed_count', 0)}"
        )
        if diff.get("changed"):
            print("  changed sample:", ", ".join(diff["changed"][:8]))
        if diff.get("added") and not diff.get("first_harvest"):
            print("  added sample:", ", ".join(diff["added"][:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
