"""The one contract every printer adapter honors.

The dispatcher only ever calls `status()` and `send()` — it knows nothing about
8899 vs Moonraker vs MQTT. That's what lets new printers drop in.
"""
from typing import Protocol


class Adapter(Protocol):
    key: str

    def status(self) -> str:
        """One of: 'idle', 'printing', 'offline'."""
        ...

    def send(self, gcode_path: str, start: bool) -> str:
        """Upload the g-code (and start it if `start`); return a remote handle."""
        ...
