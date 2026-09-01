# Persistent vendor profiles — never `/tmp`

BambuStudio / Orca vendor trees must live on a disk that survives reboot.

The 2026-08 A1 mini outage (REL-602 failure #3) was a symlink:

```
vendor_profiles/BBL -> /tmp/bambustudio-extract/squashfs-root/resources/profiles/BBL
```

A power blip cleared `/tmp`, flatten produced hollow profiles, and every slice
died as C++ `return -5`. Tests stayed green because they never opened the
output 3mf.

## Where profiles are resolved

`forge.slice.profile_resolve` looks at, in order:

1. `BAMBU_PROFILES` / `ORCA_PROFILES` (must not be under `/tmp` or `/var/tmp`)
2. This directory (`forge/slice/vendor_profiles/BBL`) if it contains real JSON
3. `~/.forge/vendor_profiles/BBL` (first-run extract target)
4. `~/print_work/multi_slicer/vendor_profiles/BBL` (legacy persistent tree)

There is **no** `/tmp/bambustudio-extract/...` fallback.

## First-run extract

```bash
# Bambu (A1 mini / A2L)
./BambuStudio_*.AppImage --appimage-extract 'resources/profiles/BBL'
mkdir -p ~/.forge/vendor_profiles
cp -a squashfs-root/resources/profiles/BBL ~/.forge/vendor_profiles/BBL
export BAMBU_PROFILES=$HOME/.forge/vendor_profiles/BBL

# Orca / Orca-Flashforge (AD5X / Ender)
./Flash.Studio_*.AppImage --appimage-extract -o ~/orcaslicer
export ORCA_PROFILES=$HOME/orcaslicer/squashfs-root/resources/profiles
```

Missing or empty trees raise in Python with the profile name — they do not
produce a broken JSON the slicer rejects as `-5`.
