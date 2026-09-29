from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Sequence

from ada.core.action_outcomes import OperationId, ProviderCapability
from ada.core.actions import (
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    EventBaseVersion,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import (
    CalendarChangeResult,
    CalendarChangeStatus,
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
        self._changed_events: dict[str, CalendarEvent] = {}
        self._cancelled: set[str] = set()
        self._applied_changes: set[str] = set()
        self._version_counter = 0
        self.create_attempts = 0

    @property
    def create_capability(self) -> ProviderCapability:
        return self._create_capability

    @property
    def effect_count(self) -> int:
        """Number of distinct synthetic external effects committed."""

        return len(self._events_by_operation)


    @property
    def update_capability(self) -> ProviderCapability:
        return ProviderCapability.IDEMPOTENT

    @property
    def cancel_capability(self) -> ProviderCapability:
        return ProviderCapability.IDEMPOTENT

    def seed_event(self, event: CalendarEvent) -> None:
        self._seeded_events.append(event)

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[CalendarEvent]:
        return tuple(
            event
            for event in self._current_events()
            if event.start < end and event.end > start
        )

    def _current_events(self) -> list[CalendarEvent]:
        events = [*self._seeded_events, *self._events_by_operation.values()]
        return [
            self._changed_events.get(event.event_id, event)
            for event in events
            if event.event_id not in self._cancelled
        ]

    def _next_version(self) -> EventVersion:
        self._version_counter += 1
        return EventVersion(f'"m{self._version_counter}"')

    def update_event(
        self,
        proposal: UpdateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        if operation_id in self._applied_changes:
            return CalendarChangeResult(
                status=CalendarChangeStatus.COMMITTED,
                event_ref=proposal.event_ref,
                event=self._changed_events.get(proposal.event_ref.resource_name),
            )
        current = self._find(proposal.event_ref)
        if current is None:
            return CalendarChangeResult(
                status=CalendarChangeStatus.ABSENT, error_code="event_absent"
            )
        if self._is_stale(current, proposal.base_version):
            return CalendarChangeResult(
                status=CalendarChangeStatus.CONFLICT, error_code="version_conflict"
            )
        changes = proposal.changes
        updated = replace(
            current,
            title=changes.title if changes.title is not None else current.title,
            start=changes.start if changes.start is not None else current.start,
            end=changes.end if changes.end is not None else current.end,
            location=(
                changes.location if changes.location is not None else current.location
            ),
            version=self._next_version(),
            sequence=current.sequence + 1,
        )
        self._changed_events[current.event_id] = updated
        self._applied_changes.add(operation_id)
        return CalendarChangeResult(
            status=CalendarChangeStatus.COMMITTED,
            event_ref=proposal.event_ref,
            event=updated,
        )

    def cancel_event(
        self,
        proposal: CancelCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        current = self._find(proposal.event_ref)
        if current is None:
            return CalendarChangeResult(
                status=CalendarChangeStatus.ABSENT, error_code="event_absent"
            )
        if self._is_stale(current, proposal.base_version):
            return CalendarChangeResult(
                status=CalendarChangeStatus.CONFLICT, error_code="version_conflict"
            )
        self._cancelled.add(current.event_id)
        return CalendarChangeResult(
            status=CalendarChangeStatus.COMMITTED, event_ref=proposal.event_ref
        )

    def _find(self, event_ref: EventRef) -> CalendarEvent | None:
        for event in self._current_events():
            if (
                event.calendar_id == event_ref.calendar_id
                and event.event_id == event_ref.resource_name
            ):
                return event
        return None

    @staticmethod
    def _is_stale(event: CalendarEvent, base: EventBaseVersion) -> bool:
        return event.version != base.version or event.sequence != base.sequence

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
                event_ref=existing.event_ref,
                event=self._changed_events.get(existing.event_id, existing),
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
            event_ref=EventRef(
                calendar_id=proposal.calendar_id,
                resource_name=f"fake-{OperationId(operation_id)}",
            ),
            version=self._next_version(),
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
            event_ref=event.event_ref,
            event=event,
        )

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        if self._create_capability is ProviderCapability.NONE:
            return None
        return self._events_by_operation.get(operation_id)
