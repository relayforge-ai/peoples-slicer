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
# Slice table uses a1mini / a2l; send config often uses a single "bambu" adapter.
_PRINTER_ALIASES: dict[str, str] = {
    "bambu_a2l": "bambu",
    "bambu_a1mini": "bambu",
    "a1mini": "bambu",
    "a2l": "bambu",
    "a1_mini": "bambu",
    "a1-mini": "bambu",
}
_SLICE_KEYS: dict[str, str] = {
    "bambu_a1mini": "a1mini",
    "bambu_a2l": "a2l",
    "bambu": "a2l",
}


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


class Dispatcher:
    """Routes classified g-code to printer adapters — send now or queue.

    Wires the four collaborators the headless flow needs:

    - ``adapters``: ``{printer_key: Adapter}`` — the only objects that touch a
      printer. The dispatcher calls just ``status()`` and ``send()`` on them
      (see ``adapters.base.Adapter``); a classifier key like ``"bambu_a2l"``
      is collapsed onto a configured adapter via ``_PRINTER_ALIASES``.
    - ``queue``: the crash-recoverable per-printer FIFO (``JobQueue``) that
      backs the send-now-vs-hold decision and survives restarts.
    - ``store``: optional event sink; when set, every emitted event is also
      written through ``store.record`` (the MakerLobster visibility seam).
    - ``guardian``: optional print-safety gate consulted after de-duplication
      and before any send; a veto becomes a ``"vetoed"`` event, never a send.

    Every routing decision — from both :meth:`submit` and :meth:`drain` — is
    funneled through :meth:`_emit`, so ``events`` holds an in-order log of every
    outcome this process produced and each returned dict carries a ``state`` key.
    """

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
        slice_key = _SLICE_KEYS.get(printer)
        if slice_key and slice_key in self.adapters:
            return slice_key
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
        """Classify and route one sliced file, returning a single result event.

        Any ``**extra`` fields (e.g. ``bed_confirmed_clear``) are merged into the
        job and forwarded to the guardian. The returned dict always carries a
        ``state`` key describing the outcome:

        - ``"quarantined"`` — no adapter matches the classified printer.
        - ``"duplicate"`` — this file's job id is already pending or active.
        - ``"vetoed"`` — the guardian refused the job (``reason`` explains why).
        - ``"printing"`` — sent to an idle printer and started.
        - ``"failed"`` — the send raised; the job is requeued at the front.
        - ``"queued"`` — accepted but held behind other work for this printer.
        """
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
            "prime_tower_enabled": getattr(info, "prime_tower_enabled", None),
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
            return self._send_job(printer, adapter, job)

        self.queue.enqueue(printer, job)
        return self._emit({**job, "job_id": job_id, "state": "queued"})

    def _send_job(self, printer: str, adapter, job: dict) -> dict:
        try:
            adapter.send(job["path"], start=True)
        except Exception as exc:  # noqa: BLE001
            self.queue.requeue_front(printer, job)
            return self._emit(
                {**job, "job_id": job["id"], "state": "failed", "reason": str(exc)}
            )
        return self._emit({**job, "job_id": job["id"], "state": "printing"})

    def retry_active(self, printer: str) -> dict:
        """Re-send an interrupted active job after the printer returns idle.

        A production stop can leave the durable queue's exact job marked active
        while the hardware is idle.  ``submit`` deliberately de-duplicates that
        file and ``drain`` interprets idle-active as completed, so neither is a
        safe retry operation.  This explicit path preserves the active identity,
        re-runs the guardian against the persisted safety facts, refuses a busy
        printer, and sends only that already-active job.
        """
        adapter_key = self._adapter_key(printer)
        if not adapter_key:
            return self._emit(
                {"state": "quarantined", "printer": printer,
                 "reason": "unknown_printer"}
            )

        job = self.queue.active(adapter_key)
        if job is None:
            return self._emit(
                {"state": "no_active", "printer": adapter_key,
                 "reason": "no interrupted active job"}
            )

        adapter = self.adapters[adapter_key]
        status = adapter.status()
        if status != "idle":
            return self._emit(
                {**job, "job_id": job["id"], "state": "busy",
                 "reason": f"printer status is {status}"}
            )

        if self.guardian is not None:
            approved, reason = self.guardian.approve(job)
            if not approved:
                return self._emit(
                    {**job, "job_id": job["id"], "state": "vetoed", "reason": reason}
                )

        return self._send_job(adapter_key, adapter, job)

    def drain(self) -> list[dict]:
        """Start the next queued job on any printer that just went idle."""
        results = []
        for printer, adapter in self.adapters.items():
            active = self.queue.active(printer)
            if active is not None:
                if adapter.status() == "idle":
                    self.queue.complete(printer, active["id"])
                else:
                    continue
            if not self.queue.pending(printer):
                continue
            if adapter.status() != "idle":
                continue
            job = self.queue.start_next(printer)
            if job is None:
                continue
            if self.guardian is not None:
                approved, reason = self.guardian.approve(job)
                if not approved:
                    self.queue.requeue_front(printer, job)
                    results.append(
                        self._emit({**job, "job_id": job["id"], "state": "vetoed", "reason": reason})
                    )
                    continue
            results.append(self._send_job(printer, adapter, job))
        return results
