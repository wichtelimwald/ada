from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from datetime import datetime
from typing import Literal, Protocol


class ActionProposal(Protocol):
    """Marker contract for typed proposals returned by an agent runtime."""

    @property
    def kind(self) -> str:
        """Stable Ada action kind."""


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


def calendar_create_action_binding(proposal: CreateCalendarEventProposal) -> str:
    """Canonical immutable identity for one calendar-create action payload."""

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
