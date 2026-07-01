from pathlib import Path

# Anchor to the repo (this file's grandparent) so the test passes regardless of the
# working directory pytest is invoked from — matters on Windows/CI runners.
MAP = Path(__file__).resolve().parents[1] / "docs" / "EXTRACTION_MAP.md"


def test_map_exists_and_covers_every_engine_module():
    text = MAP.read_text()
    for module in ("classifier", "reader", "jobqueue", "dispatcher",
                   "adapters/ad5x", "adapters/bambu", "adapters/klipper"):
        assert module in text, f"EXTRACTION_MAP missing {module}"


def test_map_states_the_secret_scrub_rule():
    text = MAP.read_text().lower()
    assert "secret" in text and "redact" in text
