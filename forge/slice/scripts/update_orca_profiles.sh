#!/usr/bin/env bash
# REL-600 — 3×/wk profile refresh helper.
# 1) Optionally pull a newer Orca AppImage (manual URL / already downloaded)
# 2) Re-harvest the installed vendor tree
# 3) Write manifest + diff under ~/.forge/harvest/
#
# Install timer (user systemd):
#   mkdir -p ~/.config/systemd/user
#   cp forge/slice/systemd/profile-harvest.* ~/.config/systemd/user/
#   systemctl --user daemon-reload
#   systemctl --user enable --now profile-harvest.timer
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONUNBUFFERED=1
LOG_DIR="${HOME}/.forge/logs"
mkdir -p "$LOG_DIR" "${HOME}/.forge/harvest"
LOG="$LOG_DIR/profile-harvest.log"
{
  echo "=== $(date -Is) profile harvest ==="
  # If a newer extracted Orca exists, prefer it
  if [[ -d "${HOME}/orcaslicer/squashfs-root/resources/profiles" ]]; then
    export ORCA_PROFILES="${HOME}/orcaslicer/squashfs-root/resources/profiles"
    echo "ORCA_PROFILES=$ORCA_PROFILES"
  fi
  python3 -u "$ROOT/scripts/harvest_profiles.py" --json
  echo "done"
} >>"$LOG" 2>&1
