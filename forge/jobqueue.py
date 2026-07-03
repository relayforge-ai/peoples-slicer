"""Persistent per-printer FIFO job queue, crash-recoverable.

State is a single JSON file written atomically on every mutation, so a restart
(`JobQueue(same_path)`) restores pending + active jobs exactly.
"""
import json
import os


class JobQueue:
    def __init__(self, state_path: str):
        self.state_path = state_path
        os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
        self._state = {"pending": {}, "active": {}}
        if os.path.exists(state_path):
            with open(state_path) as f:
                self._state = json.load(f)
        self._state.setdefault("pending", {})
        self._state.setdefault("active", {})

    def _save(self) -> None:
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._state, f, indent=2)
        os.replace(tmp, self.state_path)

    def enqueue(self, printer: str, job: dict) -> None:
        # dedup by id against anything already pending or active for this printer
        known = {j["id"] for j in self._state["pending"].get(printer, [])}
        active = self._state["active"].get(printer)
        if active:
            known.add(active["id"])
        if job["id"] in known:
            return
        self._state["pending"].setdefault(printer, []).append(job)
        self._save()

    def peek(self, printer: str) -> dict | None:
        q = self._state["pending"].get(printer, [])
        return q[0] if q else None

    def pending(self, printer: str) -> list[dict]:
        return list(self._state["pending"].get(printer, []))

    def active(self, printer: str) -> dict | None:
        return self._state["active"].get(printer)

    def start_next(self, printer: str) -> dict | None:
        q = self._state["pending"].get(printer, [])
        if not q:
            return None
        job = q.pop(0)
        self._state["active"][printer] = job
        self._save()
        return job

    def complete(self, printer: str, job_id: str) -> None:
        active = self._state["active"].get(printer)
        if active and active["id"] == job_id:
            self._state["active"][printer] = None
            self._save()

    def requeue_front(self, printer: str, job: dict) -> None:
        self._state["active"][printer] = None
        self._state["pending"].setdefault(printer, []).insert(0, job)
        self._save()
