"""Event sinks for the dispatcher. Public default = append-only jobs.jsonl."""
import json
from pathlib import Path

class JsonlStore:
    """The default dispatcher event sink: an append-only JSON-Lines log.

    Every event the dispatcher emits (``queued``, ``printing``, ``vetoed``,
    ``failed``, …) is written as one self-contained JSON object per line to
    ``path`` — the durable seam the MakerLobster mesh reads back (Seurat for
    visibility, Amos for safety). Being append-only means a crash mid-run can
    never corrupt already-written records. The parent directory is created on
    init so the first ``record`` never trips over a missing ``~/.forge`` dir.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: dict) -> None:
        """Append one event as a single JSON line (open-append-close per call)."""
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

class NullStore:
    """No-op sink honoring the same ``record(event)`` protocol — for tests / dry-run."""

    def record(self, event: dict) -> None:
        pass
