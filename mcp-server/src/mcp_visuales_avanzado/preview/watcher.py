"""File watcher for PBIR report changes.

Uses polling (stat-based) to avoid external dependencies.
Notifies a callback when any JSON file in the definition folder changes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path


class PbirWatcher:
    """Poll-based file watcher for PBIR definition folders."""

    def __init__(
        self,
        definition_path: Path,
        on_change: Callable[[], None],
        interval: float = 0.5,
    ) -> None:
        self.definition_path = definition_path
        self.on_change = on_change
        self.interval = interval
        self._running = False
        self._snapshot: dict[str, float] = {}

    def _take_snapshot(self) -> dict[str, float]:
        """Capture mtime of all JSON files."""
        snap: dict[str, float] = {}
        if not self.definition_path.is_dir():
            return snap
        for f in self.definition_path.rglob("*.json"):
            try:
                snap[str(f)] = f.stat().st_mtime
            except OSError:
                continue
        return snap

    def _detect_changes(self) -> bool:
        """Compare current state to last snapshot."""
        current = self._take_snapshot()
        changed = current != self._snapshot
        self._snapshot = current
        return changed

    def start(self) -> None:
        """Start watching (blocking). Call stop() from another thread to exit."""
        self._running = True
        self._snapshot = self._take_snapshot()

        while self._running:
            time.sleep(self.interval)
            if self._detect_changes():
                try:
                    self.on_change()
                except Exception:
                    pass  # Don't crash the watcher

    def stop(self) -> None:
        """Signal the watcher to stop."""
        self._running = False
