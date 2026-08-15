import json

import pytest

from forge.config import load_config


def test_malformed_config_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(ValueError, match="malformed"):
        load_config(str(bad))


def test_non_object_config_raises(tmp_path):
    bad = tmp_path / "list.json"
    bad.write_text("[1, 2]")
    with pytest.raises(ValueError, match="JSON object"):
        load_config(str(bad))


def test_valid_config_loads_printers(tmp_path):
    cfg_path = tmp_path / "ok.json"
    cfg_path.write_text(json.dumps({"printers": {"ad5x": {"type": "ad5x", "host": "h", "serial": "s", "checkcode": "c"}}}))
    cfg = load_config(str(cfg_path))
    assert "ad5x" in cfg["printers"]


def test_kobra_moonraker_url_env_var_adds_kobra3max(monkeypatch):
    monkeypatch.setenv("KOBRA_MOONRAKER_URL", "http://10.0.0.5:7125")
    monkeypatch.delenv("AD5X_HOST", raising=False)
    monkeypatch.delenv("BAMBU_HOST", raising=False)
    monkeypatch.delenv("MOONRAKER_URL", raising=False)

    cfg = load_config(None)

    assert cfg["printers"]["kobra3max"] == {
        "type": "klipper", "moonraker_url": "http://10.0.0.5:7125",
    }


def test_kobra_and_ender_are_independent_entries(monkeypatch):
    """Both are the same adapter class under the hood, but distinct dispatch
    targets -- config must not collapse them onto one key."""
    monkeypatch.setenv("MOONRAKER_URL", "http://10.0.0.1:7125")
    monkeypatch.setenv("KOBRA_MOONRAKER_URL", "http://10.0.0.2:7125")

    cfg = load_config(None)

    assert cfg["printers"]["ender"]["moonraker_url"] == "http://10.0.0.1:7125"
    assert cfg["printers"]["kobra3max"]["moonraker_url"] == "http://10.0.0.2:7125"
    assert cfg["printers"]["ender"] != cfg["printers"]["kobra3max"]


def test_no_env_vars_means_no_kobra_entry(monkeypatch):
    monkeypatch.delenv("FORGE_CONFIG", raising=False)
    monkeypatch.delenv("KOBRA_MOONRAKER_URL", raising=False)
    monkeypatch.delenv("AD5X_HOST", raising=False)
    monkeypatch.delenv("BAMBU_HOST", raising=False)
    monkeypatch.delenv("MOONRAKER_URL", raising=False)

    cfg = load_config(None)

    assert "kobra3max" not in cfg["printers"]
