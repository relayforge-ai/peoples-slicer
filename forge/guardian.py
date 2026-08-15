"""Amos Dawes safety guardian — deterministic reflexes + pluggable pre-send veto."""
from __future__ import annotations

from typing import Callable, Protocol


class VetoHook(Protocol):
    def __call__(self, job: dict) -> tuple[bool, str]: ...


class Guardian:
    """Deterministic safety rules that run even when every LLM is offline."""

    def __init__(self, veto_hook: VetoHook | None = None):
        self.veto_hook = veto_hook

    def approve(self, job: dict) -> tuple[bool, str]:
        """Decide whether a job may be sent, returning ``(approved, reason)``.

        The single safety gate the dispatcher calls before every send. It runs
        the deterministic reflexes first (:meth:`_deterministic_checks`) and
        short-circuits on the first failing one — these are fail-closed and run
        even when every LLM is offline, so the returned ``reason`` names the
        specific reflex that vetoed (e.g. ``"bed not confirmed clear"``). Only
        when all reflexes pass is the optional ``veto_hook`` consulted; it must
        honor the same ``(approved, reason)`` contract and its verdict is
        returned verbatim. With no hook set, an all-clear job returns
        ``(True, "ok")``. This method never raises on a malformed ``job`` dict —
        missing keys are treated as unconfirmed and veto.
        """
        approved, reason = self._deterministic_checks(job)
        if not approved:
            return approved, reason
        if self.veto_hook is not None:
            return self.veto_hook(job)
        return True, "ok"

    @staticmethod
    def _deterministic_checks(job: dict) -> tuple[bool, str]:
        if not job.get("path"):
            return False, "missing file path"
        # Fail-CLOSED: the bed must be EXPLICITLY confirmed clear (True). Missing / None /
        # False all veto — a physical safety gate must never proceed on an unconfirmed default.
        if job.get("bed_confirmed_clear") is not True:
            return False, "bed not confirmed clear"
        colors = job.get("colors", 1)
        if colors > 1 and job.get("prime_tower_enabled") is not True:
            return False, "multicolor print requires verified enable_prime_tower = 1"
        if colors > 4:
            return False, "more than 4 colors — AD5X IFS limit"
        material = (job.get("material") or "").lower()
        printer = job.get("printer")
        if "tpu" in material or "flex" in material:
            if printer != "ad5x":
                return False, "flexible material must route to AD5X"
        return True, "ok"
