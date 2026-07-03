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
        if job.get("colors", 1) > 4:
            return False, "more than 4 colors — AD5X IFS limit"
        material = (job.get("material") or "").lower()
        printer = job.get("printer")
        if "tpu" in material or "flex" in material:
            if printer != "ad5x":
                return False, "flexible material must route to AD5X"
        return True, "ok"