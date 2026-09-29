from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from datetime import datetime
from typing import Literal, Protocol


class CalendarProposalValidationError(ValueError):
    """Calendar proposal is incomplete or internally inconsistent."""


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
class EventBaseVersion:
    """The event version an update/cancel was approved against (ADR-0009
    section 6): the entity tag and the iCalendar ``SEQUENCE`` it carried."""

    version: EventVersion
    sequence: int


class ActionDraft(Protocol):
    """Incomplete model-derived action intent; never executable as-is."""

    @property
    def kind(self) -> str:
        """Stable Ada draft kind."""


class ActionProposal(Protocol):
    """Marker contract for typed proposals returned by an agent runtime."""

    @property
    def kind(self) -> str:
        """Stable Ada action kind."""


@dataclass(frozen=True, slots=True)
class CreateCalendarEventDraft:
    """Non-executable calendar intent that may contain unresolved details."""

    title: str | None
    date: str | None
    start_time: str | None
    end_time: str | None
    calendar_id: str | None
    location: str | None
    language: Literal["de", "en"]
    unresolved: tuple[str, ...]

    @property
    def kind(self) -> Literal["calendar.create.draft"]:
        return "calendar.create.draft"


@dataclass(frozen=True, slots=True)
class CreateCalendarEventProposal:
    """Typed proposal for the first representative vertical slice."""

    title: str
    start: datetime
    end: datetime
    calendar_id: str
    location: str | None = None

    @property
    def kind(self) -> Literal["calendar.create"]:
        return "calendar.create"


def validate_calendar_create_proposal(
    proposal: CreateCalendarEventProposal,
) -> None:
    """Validate Ada-owned invariants before authorization or execution."""

    if not isinstance(proposal.title, str) or not proposal.title.strip():
        raise CalendarProposalValidationError("calendar event title is required")
    if not isinstance(proposal.calendar_id, str) or not proposal.calendar_id.strip():
        raise CalendarProposalValidationError("calendar_id is required")
    if not isinstance(proposal.start, datetime) or not isinstance(proposal.end, datetime):
        raise CalendarProposalValidationError(
            "calendar event start and end must be datetimes"
        )
    if (
        proposal.start.tzinfo is None
        or proposal.start.utcoffset() is None
        or proposal.end.tzinfo is None
        or proposal.end.utcoffset() is None
    ):
        raise CalendarProposalValidationError(
            "calendar event start and end must be timezone-aware"
        )
    if proposal.end <= proposal.start:
        raise CalendarProposalValidationError(
            "calendar event end must be after start"
        )
    if proposal.location is not None and (
        not isinstance(proposal.location, str) or not proposal.location.strip()
    ):
        raise CalendarProposalValidationError(
            "calendar event location must be non-empty when provided"
        )


def calendar_create_action_binding(proposal: CreateCalendarEventProposal) -> str:
    """Canonical immutable identity for one calendar-create action payload."""

    validate_calendar_create_proposal(proposal)

    payload = {
        "kind": proposal.kind,
        "title": proposal.title,
        "start": proposal.start.isoformat(),
        "end": proposal.end.isoformat(),
        "calendar_id": proposal.calendar_id,
        "location": proposal.location,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"calendar.create:sha256:{hashlib.sha256(canonical).hexdigest()}"


@dataclass(frozen=True, slots=True)
class CalendarEventChanges:
    """Fields an update changes; ``None`` means "leave unchanged"."""

    title: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    location: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateCalendarEventProposal:
    """Typed proposal to change one existing ordinary event (ADR-0009 s6)."""

    event_ref: EventRef
    base_version: EventBaseVersion
    changes: CalendarEventChanges

    @property
    def kind(self) -> Literal["calendar.update"]:
        return "calendar.update"


@dataclass(frozen=True, slots=True)
class CancelCalendarEventProposal:
    """Typed proposal to cancel (delete) one existing ordinary event."""

    event_ref: EventRef
    base_version: EventBaseVersion

    @property
    def kind(self) -> Literal["calendar.cancel"]:
        return "calendar.cancel"


def _validate_event_target(
    event_ref: EventRef, base_version: EventBaseVersion
) -> None:
    if not isinstance(event_ref, EventRef):
        raise CalendarProposalValidationError("event_ref is required")
    if not isinstance(event_ref.calendar_id, str) or not event_ref.calendar_id.strip():
        raise CalendarProposalValidationError("event_ref.calendar_id is required")
    if (
        not isinstance(event_ref.resource_name, str)
        or not event_ref.resource_name.strip()
    ):
        raise CalendarProposalValidationError("event_ref.resource_name is required")
    if not isinstance(base_version, EventBaseVersion) or not isinstance(
        base_version.version, EventVersion
    ):
        raise CalendarProposalValidationError("base_version is required")
    if (
        not isinstance(base_version.sequence, int)
        or isinstance(base_version.sequence, bool)
        or base_version.sequence < 0
    ):
        raise CalendarProposalValidationError(
            "base_version.sequence must be a non-negative integer"
        )


def validate_calendar_update_proposal(
    proposal: UpdateCalendarEventProposal,
) -> None:
    """Validate Ada-owned invariants before authorization or execution."""

    _validate_event_target(proposal.event_ref, proposal.base_version)
    changes = proposal.changes
    if not isinstance(changes, CalendarEventChanges):
        raise CalendarProposalValidationError("changes are required")
    if (
        changes.title is None
        and changes.start is None
        and changes.end is None
        and changes.location is None
    ):
        raise CalendarProposalValidationError("an update must change something")
    if changes.title is not None and (
        not isinstance(changes.title, str) or not changes.title.strip()
    ):
        raise CalendarProposalValidationError(
            "calendar event title must be non-empty when changed"
        )
    if changes.location is not None and (
        not isinstance(changes.location, str) or not changes.location.strip()
    ):
        raise CalendarProposalValidationError(
            "calendar event location must be non-empty when changed"
        )
    for value in (changes.start, changes.end):
        if value is None:
            continue
        if not isinstance(value, datetime):
            raise CalendarProposalValidationError(
                "calendar event start and end must be datetimes"
            )
        if value.tzinfo is None or value.utcoffset() is None:
            raise CalendarProposalValidationError(
                "calendar event start and end must be timezone-aware"
            )
    if (
        changes.start is not None
        and changes.end is not None
        and changes.end <= changes.start
    ):
        raise CalendarProposalValidationError(
            "calendar event end must be after start"
        )


def validate_calendar_cancel_proposal(
    proposal: CancelCalendarEventProposal,
) -> None:
    _validate_event_target(proposal.event_ref, proposal.base_version)


def _canonical_binding(prefix: str, payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}:sha256:{hashlib.sha256(canonical).hexdigest()}"


def _target_payload(
    proposal: UpdateCalendarEventProposal | CancelCalendarEventProposal,
) -> dict[str, object]:
    return {
        "kind": proposal.kind,
        "calendar_id": proposal.event_ref.calendar_id,
        "resource_name": proposal.event_ref.resource_name,
        "base_version": str(proposal.base_version.version),
        "base_sequence": proposal.base_version.sequence,
    }


def calendar_update_action_binding(proposal: UpdateCalendarEventProposal) -> str:
    """Canonical identity of one update payload, including ``base_version``."""

    validate_calendar_update_proposal(proposal)
    changes = proposal.changes
    payload = _target_payload(proposal)
    payload.update(
        {
            "title": changes.title,
            "start": changes.start.isoformat() if changes.start else None,
            "end": changes.end.isoformat() if changes.end else None,
            "location": changes.location,
        }
    )
    return _canonical_binding("calendar.update", payload)


def calendar_cancel_action_binding(proposal: CancelCalendarEventProposal) -> str:
    """Canonical identity of one cancel payload, including ``base_version``."""

    validate_calendar_cancel_proposal(proposal)
    return _canonical_binding("calendar.cancel", _target_payload(proposal))
