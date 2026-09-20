from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, Sequence

from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import CreateCalendarEventProposal


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    calendar_id: str
    location: str | None = None


class CalendarCreateStatus(str, Enum):
    COMMITTED = "committed"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class CalendarCreateResult:
    status: CalendarCreateStatus
    event: CalendarEvent | None = None
    error_code: str | None = None


class CalendarPort(Protocol):
    """Narrow calendar boundary required by the first vertical slice."""

    @property
    def create_capability(self) -> ProviderCapability:
        """Declare provider duplicate-safety semantics for create operations."""

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
    ) -> CalendarCreateResult:
        """Attempt one create using the stable Ada operation identifier."""

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        """Return an existing committed create when it can be proven."""
