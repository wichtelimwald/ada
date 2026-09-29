from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, Sequence

from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import (
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
)


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
    sequence: int = 0


class CalendarCreateStatus(str, Enum):
    COMMITTED = "committed"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class CalendarCreateResult:
    """``event_ref`` is the deterministic provider reference Ada already
    knows once ``status`` is ``COMMITTED``: it never depends on read-back
    succeeding. ``event`` is the *verified* provider-owned event data; it is
    only present once a read-back actually confirmed it. A ``COMMITTED``
    result with ``event_ref`` set but ``event`` still ``None`` means "the
    provider accepted the write, but Ada has not verified what it stored" --
    that must not be confused with verified provider state (the provider
    owns events; ADR-0009 section 6).
    """

    status: CalendarCreateStatus
    event_ref: EventRef | None = None
    event: CalendarEvent | None = None
    error_code: str | None = None


class CalendarChangeStatus(str, Enum):
    """Outcome of one update/cancel attempt (ADR-0009 section 6)."""

    COMMITTED = "committed"
    # The event changed after approval; nothing was written.
    CONFLICT = "conflict"
    # The event no longer exists. The goal state may hold, but Ada does not
    # claim the effect as its own.
    ABSENT = "absent"
    # After an ambiguous send the event still equals ``base_version``: the
    # write provably did not apply and may be retried with the same
    # precondition.
    NOT_APPLIED = "not_applied"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class CalendarChangeResult:
    """``event`` is the *verified* post-write event; only set for a committed
    update whose read-back succeeded (as for :class:`CalendarCreateResult`)."""

    status: CalendarChangeStatus
    event_ref: EventRef | None = None
    event: CalendarEvent | None = None
    error_code: str | None = None


class CalendarPort(Protocol):
    """Narrow calendar boundary required by the first vertical slice."""

    @property
    def create_capability(self) -> ProviderCapability:
        """Declare provider duplicate-safety semantics for create operations."""

    @property
    def update_capability(self) -> ProviderCapability:
        """Declare provider duplicate-safety semantics for update operations."""

    @property
    def cancel_capability(self) -> ProviderCapability:
        """Declare provider duplicate-safety semantics for cancel operations."""

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

    def update_event(
        self,
        proposal: UpdateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        """Attempt one conditional update against ``proposal.base_version``.

        Never overwrites a version newer than ``base_version``; replaying the
        same operation must not apply twice.
        """

    def cancel_event(
        self,
        proposal: CancelCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        """Attempt one conditional cancel against ``proposal.base_version``."""
