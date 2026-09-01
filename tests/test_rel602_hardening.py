"""REL-602 — tests that catch the three real failures mocks missed."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from forge.jobqueue import JobQueue
from forge.slice import backends
from forge.slice.api import SliceError, slice_for
from forge.slice.artifact import ArtifactError, assert_sliced_artifact
from forge.slice.backends import build_backend_cmd
from forge.slice.plate_policy import MAX_SAME_PLATE_PARTS, cap_same_plate_models
from forge.slice.printers import get_printer
from forge.slice.profile_resolve import (
    ProfileIndex,
    _default_bambu_profiles,
    _is_ephemeral,
    write_flattened,
)
from forge.slice.profile_validate import LINE_WIDTH_KEYS, ProfileError

from tests.slice_helpers import (
    write_ascii_stl,
    write_sliced_3mf,
    write_studio_profile_tree,
    write_two_plate_magnet_3mf,
)


def test_no_tmp_vendor_fallback_in_profile_resolve(monkeypatch):
    monkeypatch.delenv("BAMBU_PROFILES", raising=False)
    from forge.slice.profile_resolve import _persistent_bambu_candidates

    for path in _persistent_bambu_candidates():
        assert not _is_ephemeral(path), path


def test_tmp_path_is_ephemeral():
    assert _is_ephemeral(Path("/tmp/bambustudio-extract/squashfs-root/resources/profiles/BBL"))
    assert _is_ephemeral(Path("/var/tmp/profiles/BBL"))
    assert not _is_ephemeral(Path.home() / ".forge" / "vendor_profiles" / "BBL")


def test_bambu_profiles_env_under_tmp_raises(monkeypatch):
    monkeypatch.setenv(
        "BAMBU_PROFILES",
        "/tmp/bambustudio-extract/squashfs-root/resources/profiles/BBL",
    )
    with pytest.raises(FileNotFoundError, match="tmp"):
        _default_bambu_profiles(require=True)


def test_missing_bambu_profiles_raise_instead_of_absent_path(monkeypatch, tmp_path):
    monkeypatch.delenv("BAMBU_PROFILES", raising=False)
    monkeypatch.setattr(
        "forge.slice.profile_resolve._persistent_bambu_candidates",
        lambda: [tmp_path / "nope"],
    )
    with pytest.raises(FileNotFoundError, match="persistent"):
        _default_bambu_profiles(require=True)


def test_flattened_process_keeps_flashforge_line_width(tmp_path):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    idx = ProfileIndex([tree / "Flashforge"])
    dest = tmp_path / "process.json"
    write_flattened(idx, "0.20mm Standard @FF AD5X", dest, role="process")
    data = json.loads(dest.read_text())
    for key in LINE_WIDTH_KEYS:
        assert key in data and data[key], f"missing {key} after flatten"
    assert data["type"] == "process"
    assert data["from"] == "system"


def test_process_missing_line_width_raises_before_slicer(tmp_path):
    leaf = tmp_path / "hollow.json"
    leaf.write_text(
        json.dumps({"type": "process", "from": "system", "name": "Hollow 0.20"}) + "\n"
    )
    idx = ProfileIndex([tmp_path])
    with pytest.raises(ProfileError, match="line_width"):
        write_flattened(idx, "Hollow 0.20", tmp_path / "out.json", role="process")


def test_line_width_copied_onto_missing_specific_keys(tmp_path):
    leaf = tmp_path / "partial.json"
    leaf.write_text(
        json.dumps(
            {
                "type": "process",
                "from": "system",
                "name": "Partial 0.20",
                "line_width": "0.42",
            }
        )
        + "\n"
    )
    dest = tmp_path / "out.json"
    write_flattened(ProfileIndex([tmp_path]), "Partial 0.20", dest, role="process")
    data = json.loads(dest.read_text())
    assert data["initial_layer_line_width"] == "0.42"
    assert data["inner_wall_line_width"] == "0.42"


def test_artifact_assertion_reads_printer_model_and_bed(tmp_path):
    good = write_sliced_3mf(
        tmp_path / "a1mini.gcode.3mf",
        printer_model="Bambu Lab A1 mini",
        printable_area=["0x0", "180x0", "180x180", "0x180"],
    )
    cfg = assert_sliced_artifact(good, "a1mini")
    assert cfg["printer_model"] == "Bambu Lab A1 mini"

    wrong_bed = write_sliced_3mf(
        tmp_path / "crash.gcode.3mf",
        printer_model="Bambu Lab A1 mini",
        printable_area=["0x0", "256x0", "256x256", "0x256"],
    )
    with pytest.raises(ArtifactError, match="256"):
        assert_sliced_artifact(wrong_bed, "a1mini")

    empty = tmp_path / "empty.gcode.3mf"
    import zipfile

    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("Metadata/project_settings.config", "{}")
    with pytest.raises(ArtifactError, match="empty"):
        assert_sliced_artifact(empty, "a1mini")


def test_build_backend_cmd_accepts_multiple_models(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    a = write_ascii_stl(tmp_path / "a.stl", dz=8)
    b = write_ascii_stl(tmp_path / "b.stl", dz=9)
    spec = get_printer("a1mini")
    cmd = build_backend_cmd(
        spec, [a, b], tmp_path / "out.gcode.3mf", profile_dir=tmp_path / "flat"
    )
    assert str(a) in cmd.argv and str(b) in cmd.argv
    assert cmd.argv[cmd.argv.index("--slice") + 1] == "1"
    process = json.loads(Path(cmd.flattened_process).read_text())
    for key in LINE_WIDTH_KEYS:
        assert process[key]


def test_same_plate_capped_at_two_similar_heights(tmp_path):
    low = write_ascii_stl(tmp_path / "low.stl", dz=18)
    mid = write_ascii_stl(tmp_path / "mid.stl", dz=20)
    tall = write_ascii_stl(tmp_path / "tall.stl", dz=44)
    kept, notes = cap_same_plate_models([low, mid, tall])
    assert len(kept) <= MAX_SAME_PLATE_PARTS
    assert any("capped" in n for n in notes)
    # 18 vs 44 must not survive together
    names = {p.name for p in kept}
    assert not ({"low.stl", "tall.stl"} <= names)


def test_mixed_height_pair_slices_primary_only(tmp_path):
    head = write_ascii_stl(tmp_path / "head.stl", dz=44)
    tail = write_ascii_stl(tmp_path / "tail.stl", dz=18)
    kept, notes = cap_same_plate_models([head, tail])
    assert kept == [head]
    assert any("mixed-height" in n for n in notes)


def test_slice_for_passes_two_models_on_cmd(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    a = write_ascii_stl(tmp_path / "a.stl", dz=8)
    b = write_ascii_stl(tmp_path / "b.stl", dz=9)
    result = slice_for(a, "a1mini", dry_run=True, extra_models=[b])
    export_at = result.cmd.index("--export-3mf")
    models = result.cmd[export_at + 2 :]
    assert len(models) == 2
    assert str(a.resolve()) in models
    assert str(b.resolve()) in models


def test_magnet_extras_are_not_arranged(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    project = write_two_plate_magnet_3mf(tmp_path / "magnets.3mf")
    extra = write_ascii_stl(tmp_path / "extra.stl")
    result = slice_for(project, "a1mini", dry_run=True, extra_models=[extra])
    export_at = result.cmd.index("--export-3mf")
    models = result.cmd[export_at + 2 :]
    assert models == [str(project.resolve())]


def test_classifier_keys_resolve_on_slice_table():
    assert get_printer("bambu_a1mini").key == "a1mini"
    assert get_printer("bambu_a2l").key == "a2l"


def test_queue_drops_ghost_paths_on_load(tmp_path):
    state = tmp_path / "queue.json"
    missing = tmp_path / "deleted" / "job.gcode.3mf"
    alive = tmp_path / "alive.gcode"
    alive.write_text("; printer_model = Flashforge AD5X\n")
    q = JobQueue(str(state))
    q.enqueue("a1mini", {"id": "ghost", "path": str(missing), "name": "ghost.gcode.3mf"})
    q.enqueue("a1mini", {"id": "ok", "path": str(alive), "name": "alive.gcode"})
    reloaded = JobQueue(str(state))
    ids = [j["id"] for j in reloaded.pending("a1mini")]
    assert "ghost" not in ids
    assert "ok" in ids
    assert any(g["id"] == "ghost" for g in reloaded.dropped_ghosts)


def test_a1mini_flatten_has_180_bed_and_identity(tmp_path, monkeypatch):
    """The assertion shape that would have caught the /tmp symlink outage."""
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    stl = write_ascii_stl(tmp_path / "cube.stl")
    result = slice_for(stl, "a1mini", dry_run=True)
    assert result.estimates["printer_model"] == "Bambu Lab A1 mini"
    assert result.estimates["printable_area"] == ["0x0", "180x0", "180x180", "0x180"]


@pytest.mark.slow
@pytest.mark.parametrize("printer", ["a1mini", "a2l", "ad5x", "ender"])
def test_real_slice_artifact_printer_model_and_bed(printer, tmp_path):
    """One real slice per printer — skip only when the slicer binary is absent."""
    spec = get_printer(printer)
    if spec.backend == "bambu":
        binary = Path(
            os.environ.get(
                "BAMBU_STUDIO_BIN",
                str(Path.home() / "Desktop" / "BambuStudio_ubuntu24.04_v02.07.01.62.AppImage"),
            )
        )
        if not binary.is_file() or not shutil.which("xvfb-run"):
            pytest.skip(f"no BambuStudio / xvfb-run for {printer}")
    else:
        root = Path(
            os.environ.get("ORCA_ROOT", str(Path.home() / "orcaslicer" / "squashfs-root"))
        )
        if not (root / "bin" / "orca-slicer").is_file() or not shutil.which("xvfb-run"):
            pytest.skip(f"no Orca / xvfb-run for {printer}")

    stl = write_ascii_stl(tmp_path / "cube.stl", dx=15, dy=15, dz=8)
    out = tmp_path / f"{printer}.gcode.3mf" if spec.backend == "bambu" else tmp_path / f"{printer}.gcode"
    result = slice_for(stl, printer, output=out, timeout=180)
    assert result.ok is True
    assert_sliced_artifact(result.output, printer)
