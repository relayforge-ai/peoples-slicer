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