"""Magnet plate default: glue-in / non-captured only (2026-09-01 Telchar rule).

Today's Jules miss — fill-20260901-a1mini-flexypup /
``pv-flexy-pup-magnet-and-keychain-magnet`` — is this class: a two-plate
magnet 3mf. ``--slice 1`` hits the captured plate. This file is the test
that would have caught it.
"""
from __future__ import annotations

import pytest

from forge.slice import backends
from forge.slice.api import SliceError, slice_for
from forge.slice.magnet_plates import (
    MagnetPlateError,
    classify_magnet_label,
    list_project_plates,
    prefer_non_captive_path,
    select_magnet_plate,
)
from forge.slice.plate_policy import plan_plate
from forge.slice.profile_resolve import ProfileIndex

from tests.slice_helpers import write_ascii_stl, write_studio_profile_tree, write_two_plate_magnet_3mf


def test_classify_prefers_non_captive_over_captive_substring():
    assert classify_magnet_label("non-captive") == "glue_in"
    assert classify_magnet_label("non-captured") == "glue_in"
    assert classify_magnet_label("glue-in") == "glue_in"
    assert classify_magnet_label("Glue in magnets") == "glue_in"
    assert classify_magnet_label("open") == "glue_in"
    assert classify_magnet_label("Captured magnets") == "captured"
    assert classify_magnet_label("captive") == "captured"
    assert classify_magnet_label("flexy pup") is None


def test_catalog_pair_prefers_non_captive(tmp_path):
    captive = tmp_path / "pv-mini-cow-magnet-captive.3mf"
    non = tmp_path / "pv-mini-cow-magnet-non-captive.3mf"
    captive.write_bytes(b"x")
    non.write_bytes(b"x")
    assert prefer_non_captive_path([captive, non]) == non
    assert prefer_non_captive_path([non, captive]) == non


def test_list_two_plate_magnet_project(tmp_path):
    project = write_two_plate_magnet_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    plates = list_project_plates(project)
    assert [p.index for p in plates] == [1, 2]
    assert plates[0].kind == "captured"
    assert plates[1].kind == "glue_in"


def test_default_selects_glue_in_plate_not_captured(tmp_path):
    project = write_two_plate_magnet_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    decision = select_magnet_plate(project)
    assert decision.slice_plate == 2
    assert decision.style == "glue_in"
    assert decision.is_magnet_project is True
    assert any("ignored" in n and "captured" in n.lower() for n in decision.notes)
    assert "1:" in " ".join(decision.skipped)


def test_explicit_captured_style_selects_plate_one(tmp_path):
    project = write_two_plate_magnet_3mf(tmp_path / "magnets.3mf")
    decision = select_magnet_plate(project, style="captured")
    assert decision.slice_plate == 1
    assert decision.style == "captured"


def test_captured_only_project_refuses_glue_in_default(tmp_path):
    project = write_two_plate_magnet_3mf(
        tmp_path / "only-captured.3mf",
        captured_name="Captured",
        glue_name="Supports",
        captured_object="pup-captured",
        glue_object="pup-supports",
    )
    # Rename plate 2 so it is not glue-in
    with pytest.raises(MagnetPlateError, match="glue-in"):
        select_magnet_plate(project, style="glue_in")


def test_captive_sku_filename_refuses_without_explicit_request(tmp_path):
    stl = write_ascii_stl(tmp_path / "pv-mini-cow-magnet-captive.stl")
    with pytest.raises(MagnetPlateError, match="captured-only"):
        select_magnet_plate(stl)


def test_plan_plate_does_not_treat_magnet_as_multipart(tmp_path):
    project = write_two_plate_magnet_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    extra = write_ascii_stl(tmp_path / "other.stl")
    policy = plan_plate(
        project, "a1mini", goal="single", extra_models=[extra]
    )
    assert policy.slice_plate == 2
    assert policy.extra_models == []
    assert policy.multi_plate_models == []
    assert any("not a multi-part" in n for n in policy.notes)


def test_two_plate_magnet_project_slices_glue_in_only(tmp_path, monkeypatch):
    """THE test for fill-20260901-a1mini-flexypup.

    A two-plate magnet 3mf must dry-run with ``--slice 2`` (glue-in) and a
    single model path. Arranging captured+glue-in together is the spaghetti /
    wrong-plate failure mode.
    """
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    project = write_two_plate_magnet_3mf(
        tmp_path / "pv-flexy-pup-magnet-and-keychain-magnet.3mf"
    )
    result = slice_for(project, "a1mini", dry_run=True)
    assert result.ok is True
    assert result.slice_plate == 2
    idx = result.cmd.index("--slice")
    assert result.cmd[idx + 1] == "2"
    # trailing args are models — only the project, never a second extracted plate
    export_at = result.cmd.index("--export-3mf")
    models = result.cmd[export_at + 2 :]
    assert models == [str(project.resolve())]
    assert result.plate_label.lower().startswith("glue")


def test_slice_for_captured_style_uses_plate_one(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    project = write_two_plate_magnet_3mf(tmp_path / "magnets.3mf")
    result = slice_for(project, "a1mini", dry_run=True, magnet_style="captured")
    assert result.cmd[result.cmd.index("--slice") + 1] == "1"


def test_slice_for_refuses_captured_only_default(tmp_path, monkeypatch):
    tree = write_studio_profile_tree(tmp_path / "profiles")
    monkeypatch.setattr(backends, "bambu_index", lambda: ProfileIndex([tree / "BBL"]))
    project = write_two_plate_magnet_3mf(
        tmp_path / "captive-only.3mf",
        captured_name="Captive",
        glue_name="Something else",
        captured_object="pup-captive",
        glue_object="pup-other",
    )
    with pytest.raises(SliceError, match="glue-in"):
        slice_for(project, "a1mini", dry_run=True)
