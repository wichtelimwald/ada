from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, Sequence

from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import CreateCalendarEventProposal


class CalendarAudience(str, Enum):
    """Who a configured calendar's disclosure/busy semantics are scoped to."""

    PERSON = "person"
    FAMILY = "family"


class CalendarAccessMode(str, Enum):
    """Ada's configured write permission for one calendar (ADR-0009 section 3)."""

    READ = "read"
    WRITE = "write"


@dataclass(frozen=True, slots=True)
class CalendarRef:
    """Ada calendar key mapped to one configured provider collection.

    ``provider_collection`` is an opaque handle interpreted only by the
    adapter (for example a CalDAV collection URL); it never carries a
    provider-specific type across this boundary.
    """

    calendar_id: str
    provider_collection: str
    audience: CalendarAudience
    access_mode: CalendarAccessMode


class EventVersion(str):
    """Opaque provider version for one event resource (a normalized entity tag)."""

    def __new__(cls, value: str) -> "EventVersion":
        normalized = value.strip()
        if not normalized:
            raise ValueError("event version must not be empty")
        return str.__new__(cls, normalized)


@dataclass(frozen=True, slots=True)
class EventRef:
    """Provider-neutral address for one event resource within a calendar."""

    calendar_id: str
    resource_name: str


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    calendar_id: str
    location: str | None = None
    event_ref: EventRef | None = None
    version: EventVersion | None = None
    busy: bool = True
    all_day: bool = False
    recurring: bool = False
    has_attendees: bool = False


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
