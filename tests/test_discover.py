import json

from forge import discover


def test_probe_host_aggregates_fingerprints():
    def fake_prober(host: str):
        if host == "10.0.0.5":
            return [
                discover.DiscoveredPrinter(host=host, kind="klipper", model="ender", needs_credentials=False),
            ]
        return []

    found = discover.scan_hosts(["10.0.0.1", "10.0.0.5"], prober=fake_prober)
    assert len(found) == 1
    assert found[0].kind == "klipper"


def test_merge_into_config_writes_printer(tmp_path):
    path = tmp_path / "forge_config.json"
    discover.merge_into_config(
        "ender",
        {"type": "klipper", "moonraker_url": "http://10.0.0.5:7125"},
        config_path=str(path),
    )
    cfg = json.loads(path.read_text())
    assert cfg["printers"]["ender"]["moonraker_url"] == "http://10.0.0.5:7125"


def test_printer_config_entry_shapes():
    moon = discover.DiscoveredPrinter(
        host="10.0.0.5",
        kind="klipper",
        detail={"moonraker_url": "http://10.0.0.5:7125"},
        needs_credentials=False,
    )
    assert discover.printer_config_entry(moon)["type"] == "klipper"

    ad5x = discover.DiscoveredPrinter(host="10.0.0.6", kind="ad5x")
    entry = discover.printer_config_entry(ad5x, {"serial": "SN1", "checkcode": "abc"})
    assert entry == {"type": "ad5x", "host": "10.0.0.6", "serial": "SN1", "checkcode": "abc"}


def test_iter_subnet_hosts_skips_network_and_broadcast():
    hosts = discover.iter_subnet_hosts("192.168.4.0/30")
    assert "192.168.4.1" in hosts
    assert "192.168.4.2" in hosts
    assert "192.168.4.0" not in hosts