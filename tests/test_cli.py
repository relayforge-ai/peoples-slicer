import forge
from forge import cli


def test_version_is_semver():
    parts = forge.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_banner_carries_the_brand_and_funnel():
    b = cli.banner()
    assert "Telchar's Forge" in b
    assert "The People's Slicer" in b
    assert "you slice, it does the rest." in b        # verbatim tagline
    assert "telchar.relayforge.tools" in b            # the funnel, always


def test_help_lists_core_and_slice_subcommands(capsys):
    rc = cli.main(["--help"])
    out = capsys.readouterr().out
    for sub in ("discover", "review", "send", "status", "watch", "slice", "slice-send", "harvest"):
        assert sub in out
    assert rc == 0


def test_bare_invocation_prints_banner_and_succeeds(capsys):
    rc = cli.main([])
    out = capsys.readouterr().out
    assert "telchar.relayforge.tools" in out
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
