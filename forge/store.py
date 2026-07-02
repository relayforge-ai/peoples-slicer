"""Event sinks for the dispatcher. Public default = append-only jobs.jsonl."""
import json
from pathlib import Path

class JsonlStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: dict) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

class NullStore:
    def record(self, event: dict) -> None:  # for tests / dry-run
        pass
