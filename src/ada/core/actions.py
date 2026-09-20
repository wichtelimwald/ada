from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from datetime import datetime
from typing import Literal, Protocol


class CalendarProposalValidationError(ValueError):
    """Calendar proposal is incomplete or internally inconsistent."""


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
