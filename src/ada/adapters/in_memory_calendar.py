from __future__ import annotations

from datetime import datetime
from typing import Sequence

from ada.core.action_outcomes import OperationId, ProviderCapability
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import (
    CalendarCreateResult,
    CalendarCreateStatus,
    CalendarEvent,
    CalendarPort,
)


class InMemoryCalendarAdapter(CalendarPort):
    """Synthetic calendar used by the first vertical slice and tests."""

    def __init__(
        self,
        *,
        create_capability: ProviderCapability = ProviderCapability.RECONCILABLE,
        ambiguous_after_commit_once: bool = False,
        reject_creates: bool = False,
    ) -> None:
        self._create_capability = create_capability
        self._ambiguous_after_commit_once = ambiguous_after_commit_once
        self._reject_creates = reject_creates
        self._events_by_operation: dict[str, CalendarEvent] = {}
        self._seeded_events: list[CalendarEvent] = []
        self.create_attempts = 0

    @property
    def create_capability(self) -> ProviderCapability:
        return self._create_capability

    def seed_event(self, event: CalendarEvent) -> None:
        self._seeded_events.append(event)

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[CalendarEvent]:
        events = [*self._seeded_events, *self._events_by_operation.values()]
        return tuple(
            event
            for event in events
            if event.start < end and event.end > start
        )

    def create_event(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarCreateResult:
        self.create_attempts += 1

        existing = self._events_by_operation.get(operation_id)
        if existing is not None:
            return CalendarCreateResult(
                status=CalendarCreateStatus.COMMITTED,
                event=existing,
            )

        if self._reject_creates:
            return CalendarCreateResult(
                status=CalendarCreateStatus.REJECTED,
                error_code="fake_rejected",
            )

        event = CalendarEvent(
            event_id=f"fake-{OperationId(operation_id)}",
            title=proposal.title,
            start=proposal.start,
            end=proposal.end,
            calendar_id=proposal.calendar_id,
            location=proposal.location,
        )
        self._events_by_operation[operation_id] = event

        if self._ambiguous_after_commit_once:
            self._ambiguous_after_commit_once = False
            return CalendarCreateResult(
                status=CalendarCreateStatus.AMBIGUOUS,
                error_code="fake_response_lost_after_commit",
            )

        return CalendarCreateResult(
            status=CalendarCreateStatus.COMMITTED,
            event=event,
        )

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        if self._create_capability is ProviderCapability.NONE:
            return None
        return self._events_by_operation.get(operation_id)
