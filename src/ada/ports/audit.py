from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    operation_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


class AuditEventPort(Protocol):
    """Privacy-conscious operational/security event sink."""

    def record(self, event: AuditEvent) -> None:
        """Record an event without assuming private prompt/content logging."""
