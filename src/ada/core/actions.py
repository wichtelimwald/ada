from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
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
