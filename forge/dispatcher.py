"""Route a sliced g-code file to the right printer — send now or queue.

Deterministic, no LLM in the hot path. Emits an event per submit; if a `store`
is given, every event is also written through (the seam the MakerLobster mesh
reads — Seurat for visibility, Amos for safety).
"""
import hashlib
import os

from .jobqueue import JobQueue
from .reader import classify_file

# Classifier may return specific Bambu keys before both printers are wired in config.
_PRINTER_ALIASES: dict[str, str] = {
    "bambu_a2l": "bambu",
    "bambu_a1mini": "bambu_a1mini",
}


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


class Dispatcher:
    def __init__(self, adapters: dict, queue: JobQueue, store=None, guardian=None):
        self.adapters = adapters
        self.queue = queue
        self.store = store
        self.guardian = guardian
        self.events: list[dict] = []

    def _emit(self, event: dict) -> dict:
        self.events.append(event)
        if self.store is not None:
            self.store.record(event)
        return event

    def _adapter_key(self, printer: str | None) -> str | None:
        if not printer:
            return None
        if printer in self.adapters:
            return printer
        alias = _PRINTER_ALIASES.get(printer)
        if alias and alias in self.adapters:
            return alias
        return None

    def _known(self, printer: str, job_id: str) -> bool:
        ids = {j["id"] for j in self.queue.pending(printer)}
        active = self.queue.active(printer)
        if active:
            ids.add(active["id"])
        return job_id in ids

    def submit(self, path: str, **extra) -> dict:
        info = classify_file(path)
        name = os.path.basename(path)

        adapter_key = self._adapter_key(info.printer)
        if not adapter_key:
            return self._emit(
                {"state": "quarantined", "name": name,
                 "printer": info.printer, "reason": "unknown_printer"}
            )

        printer = adapter_key
        job_id = _hash_file(path)
        job = {
            "id": job_id, "name": name, "printer": printer, "path": path,
            "material": info.material, "colors": info.colors,
            "est_seconds": info.est_seconds, "est_grams": info.est_grams,
            **extra,
        }

        if self._known(printer, job_id):
            return self._emit({**job, "job_id": job_id, "state": "duplicate"})

        if self.guardian is not None:
            approved, reason = self.guardian.approve(job)
            if not approved:
                return self._emit(
                    {**job, "job_id": job_id, "state": "vetoed", "reason": reason}
                )

        adapter = self.adapters[printer]
        can_send_now = (
            self.queue.active(printer) is None
            and not self.queue.pending(printer)
            and adapter.status() == "idle"
        )
        if can_send_now:
            self.queue.enqueue(printer, job)
            self.queue.start_next(printer)
            adapter.send(path, start=True)
            return self._emit({**job, "job_id": job_id, "state": "printing"})

        self.queue.enqueue(printer, job)
        return self._emit({**job, "job_id": job_id, "state": "queued"})

    def drain(self) -> list[dict]:
        """Start the next queued job on any printer that just went idle."""
        results = []
        for printer, adapter in self.adapters.items():
            if self.queue.active(printer) is not None:
                continue
            if not self.queue.pending(printer):
                continue
            if adapter.status() != "idle":
                continue
            job = self.queue.start_next(printer)
            adapter.send(job["path"], start=True)
            results.append(self._emit({**job, "job_id": job["id"], "state": "printing"}))
        return results
