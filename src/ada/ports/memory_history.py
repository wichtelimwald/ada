from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class MemoryHistoryPort(Protocol):
    """Recovery/versioning history kept separate from current Memory semantics."""

    def capture_snapshot(
        self,
        snapshot: Mapping[str, bytes],
        *,
        reason: str,
    ) -> bool:
        """Capture a domain snapshot and return whether a revision was created."""

    def has_seen_entry_id(self, entry_id: str) -> bool:
        """Return whether an entry identity has appeared in any history revision."""
