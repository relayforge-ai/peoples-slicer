import json
import time

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


# --- REL-631: scan_hosts must be concurrent and must stream, not silently buffer ---
# Found via a cold-start test: a sequential scan of a full /24 with unresponsive hosts is
# a genuine, silent multi-minute wait (up to ~19 min at the default per-probe timeout,
# confirmed against real source) with zero output until the very end — indistinguishable
# from a hang.


def test_scan_hosts_runs_concurrently_not_sequentially():
    """20 hosts, each probe taking 0.2s if run one at a time = 4s+ sequential. A truly
    concurrent scan with enough workers should overlap those waits and finish in a small
    fraction of that. This is a real behavioural proof, not just a code-shape check —
    it would fail against the old strictly-sequential `for host in hosts: probe(host)`."""

    def slow_prober(host: str):
        time.sleep(0.2)
        return []

    hosts = [f"10.0.0.{i}" for i in range(20)]
    start = time.monotonic()
    discover.scan_hosts(hosts, prober=slow_prober, max_workers=20)
    elapsed = time.monotonic() - start

    sequential_worst_case = 0.2 * len(hosts)  # 4.0s
    assert elapsed < sequential_worst_case / 2, (
        f"scan_hosts took {elapsed:.2f}s for {len(hosts)} hosts at 0.2s each — "
        f"expected well under {sequential_worst_case:.2f}s if truly concurrent"
    )


def test_scan_hosts_still_returns_full_aggregated_list():
    """The existing return contract (a list every caller — including --save's `len(found)
    != 1` check — depends on) must survive the concurrency rewrite unchanged."""

    def fake_prober(host: str):
        if host in ("10.0.0.5", "10.0.0.9"):
            return [discover.DiscoveredPrinter(host=host, kind="klipper", needs_credentials=False)]
        return []

    hosts = [f"10.0.0.{i}" for i in range(15)]
    found = discover.scan_hosts(hosts, prober=fake_prober, max_workers=8)
    assert isinstance(found, list)
    assert len(found) == 2
    assert {p.host for p in found} == {"10.0.0.5", "10.0.0.9"}


def test_scan_hosts_streams_results_as_found():
    """`on_result` must fire per hit as it's found, not only after the whole scan
    completes — this is the actual fix for 'silence looks like a hang'."""

    def fake_prober(host: str):
        if host == "10.0.0.7":
            return [discover.DiscoveredPrinter(host=host, kind="ad5x", needs_credentials=True)]
        return []

    streamed: list[discover.DiscoveredPrinter] = []
    hosts = [f"10.0.0.{i}" for i in range(10)]
    found = discover.scan_hosts(hosts, prober=fake_prober, max_workers=8, on_result=streamed.append)

    assert streamed == found
    assert len(streamed) == 1
    assert streamed[0].host == "10.0.0.7"


def test_scan_hosts_reports_progress_to_completion():
    """`on_progress(done, total)` must fire once per completed host and reach
    (total, total) — the throttled-print CLI layer depends on this to know when to stop."""

    def fake_prober(host: str):
        return []

    progress_calls: list[tuple[int, int]] = []
    hosts = [f"10.0.0.{i}" for i in range(12)]
    discover.scan_hosts(
        hosts,
        prober=fake_prober,
        max_workers=6,
        on_progress=lambda done, total: progress_calls.append((done, total)),
    )

    assert len(progress_calls) == len(hosts)
    assert progress_calls[-1] == (len(hosts), len(hosts))
    # done must be monotonically increasing
    assert [c[0] for c in progress_calls] == sorted(c[0] for c in progress_calls)


def test_scan_hosts_empty_host_list_is_a_noop():
    calls = []
    found = discover.scan_hosts([], prober=lambda h: [], on_progress=calls.append)
    assert found == []
    assert calls == []