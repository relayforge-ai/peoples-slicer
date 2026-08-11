import forge
from forge import cli


def test_version_is_semver():
    parts = forge.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_banner_is_peoples_slicer_not_telchar():
    b = cli.banner()
    assert "People's Slicer" in b
    assert "forge" in b.lower()
    assert "telchar" not in b.lower()
    assert "relayforge.tools" not in b.lower()


def test_help_lists_core_and_slice_subcommands(capsys):
    rc = cli.main(["--help"])
    out = capsys.readouterr().out
    for sub in ("discover", "review", "send", "status", "watch", "slice", "slice-send", "harvest", "gui"):
        assert sub in out
    assert rc == 0


def test_bare_invocation_prints_banner_and_succeeds(capsys):
    rc = cli.main([])
    out = capsys.readouterr().out
    assert "People's Slicer" in out
    assert "telchar.relayforge.tools" not in out
    assert rc == 0


def test_review_command_runs_on_golden_fixture(capsys):
    from pathlib import Path

    from forge import fixtures

    path = Path(fixtures.FIXTURES_ROOT) / "ender" / "golden.gcode"
    rc = cli.main(["review", str(path)])
    out = capsys.readouterr().out
    assert "findings" in out
    assert rc == 0


def test_discover_host_flag_does_not_scan_whole_subnet(capsys, monkeypatch):
    monkeypatch.setattr(
        "forge.discover.probe_host",
        lambda host: [
            __import__("forge.discover", fromlist=["DiscoveredPrinter"]).DiscoveredPrinter(
                host=host, kind="klipper", model="test"
            )
        ],
    )
    rc = cli.main(["discover", "--host", "10.0.0.9"])
    out = capsys.readouterr().out
    assert "klipper" in out
    assert rc == 0
