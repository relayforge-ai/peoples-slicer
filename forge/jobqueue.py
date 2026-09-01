"""Persistent per-printer FIFO job queue, crash-recoverable.

State is a single JSON file written atomically on every mutation, so a restart
(`JobQueue(same_path)`) restores pending + active jobs exactly. A pre-existing
but corrupt state file raises a clear `ValueError` naming the file (mirroring
`forge.config.load_config`) rather than leaking a bare `JSONDecodeError` or
silently discarding the user's queued jobs.
"""
import json
import os


class JobQueue:
    """Per-printer FIFO of jobs plus at most one active job, persisted on disk.

    State is ``{"pending": {printer: [job, ...]}, "active": {printer: job|None}}``,
    where each ``job`` is a dict carrying at least an ``"id"``. Jobs for a printer
    wait in that printer's ``pending`` FIFO until :meth:`start_next` promotes the
    front one to ``active`` — one printer runs one job at a time. The module
    docstring covers the on-disk format and crash recovery; this documents the
    in-memory contract callers (the :class:`~forge.dispatcher.Dispatcher`) rely on:

    - :meth:`enqueue` appends to the FIFO but is a **no-op for a duplicate id** —
      one already pending or active for that printer — so re-submitting the same
      file can't double-queue it.
    - :meth:`peek` / :meth:`active` return the front pending job / the running
      job (or ``None``) without mutating anything.
    - :meth:`pending` returns a **copy** of the FIFO; mutating the result leaves
      the queue untouched.
    - :meth:`start_next` pops the front pending job and records it as ``active``,
      returning it (or ``None`` when nothing is pending).
    - :meth:`complete` clears ``active`` only when the id **matches**, so a stale
      completion for an already-replaced job is safely ignored.
    - :meth:`requeue_front` clears ``active`` and pushes the job back to the
      **front** of pending — used on a failed send so it is retried first.

    Every mutation persists immediately (atomic tmp-write + replace), so the file
    always matches memory and a restart restores pending + active exactly.
    """

    def __init__(self, state_path: str):
        self.state_path = state_path
        os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
        self._state = {"pending": {}, "active": {}}
        if os.path.exists(state_path):
            with open(state_path) as f:
                try:
                    loaded = json.load(f)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"malformed forge queue state JSON: {state_path}"
                    ) from exc
            if not isinstance(loaded, dict):
                raise ValueError(
                    f"forge queue state must be a JSON object: {state_path}"
                )
            self._state = loaded
        self._state.setdefault("pending", {})
        self._state.setdefault("active", {})
        self.dropped_ghosts: list[dict] = self._drop_missing_paths()

    def _job_path_missing(self, job: dict | None) -> bool:
        if not job or not isinstance(job, dict):
            return False
        path = job.get("path")
        if not path:
            return False
        return not os.path.isfile(path)

    def _drop_missing_paths(self) -> list[dict]:
        """Drop queued jobs whose file was deleted (dead /tmp scratchpads).

        REL-602: ``~/.forge_queue.json`` inherited three jobs pointing at a
        deleted session scratchpad and blocked dispatch. Missing path = ghost.
        Jobs without a ``path`` key are left alone (tests / metadata-only).
        """
        dropped: list[dict] = []
        pending = self._state.get("pending") or {}
        dirty = False
        for printer, jobs in list(pending.items()):
            kept = []
            for job in jobs or []:
                if self._job_path_missing(job):
                    dropped.append({**job, "printer": printer, "reason": "path_missing"})
                    dirty = True
                else:
                    kept.append(job)
            pending[printer] = kept
        active = self._state.get("active") or {}
        for printer, job in list(active.items()):
            if self._job_path_missing(job):
                dropped.append({**(job or {}), "printer": printer, "reason": "path_missing"})
                active[printer] = None
                dirty = True
        if dirty:
            self._save()
        return dropped

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
