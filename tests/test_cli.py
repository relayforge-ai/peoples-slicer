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


def test_help_lists_the_five_subcommands(capsys):
    rc = cli.main(["--help"])
    out = capsys.readouterr().out
    for sub in ("discover", "review", "send", "status", "watch"):
        assert sub in out
    assert rc == 0


def test_bare_invocation_prints_banner_and_succeeds(capsys):
    rc = cli.main([])
    out = capsys.readouterr().out
    assert "telchar.relayforge.tools" in out
    assert rc == 0
