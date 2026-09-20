from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from ada.core.actions import CreateCalendarEventProposal


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    calendar_id: str
    location: str | None = None


class CalendarPort(Protocol):
    """Narrow calendar boundary required by the first vertical slice."""

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[CalendarEvent]:
        """Return events relevant to a conflict check."""

    def create_event(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarEvent:
        """Create one event using a stable Ada operation identifier."""

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        """Resolve whether an ambiguous create already committed."""
