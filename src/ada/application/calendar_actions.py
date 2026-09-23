from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from enum import Enum
from typing import Sequence

from ada.core.action_outcomes import (
    ActionExecutionResult,
    AuthorizationEvidence,
    BusinessOutcomeStatus,
    OperationId,
)
from ada.core.actions import (
    CreateCalendarEventProposal,
    validate_calendar_create_proposal,
)
from ada.core.authorization import AuthorizationRequest, GuardDecision
from ada.ports.calendar import CalendarEvent
from ada.ports.durable_action import DurableActionPort, DurableCalendarCreate
from ada.ports.guard import AdaGuard
from ada.ports.travel_time import TravelTimePort


@dataclass(frozen=True, slots=True)
class CalendarActionResponse:
    guard: GuardDecision
    execution: ActionExecutionResult | None


class CalendarActionService:
    """Validate, authorize, then hand one typed action to durable execution."""

    def __init__(self, *, guard: AdaGuard, durable_actions: DurableActionPort) -> None:
        self._guard = guard
        self._durable_actions = durable_actions

    def create_event(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        operation_id: OperationId,
        authorization: AuthorizationRequest,
    ) -> CalendarActionResponse:
        # Reject incomplete/contradictory action data before authorization or
        # durable/provider execution. Authority checks must not double as data
        # validation.
        validate_calendar_create_proposal(proposal)

        # Privileged action/resource are derived from the typed proposal, not
        # trusted from model/tool-supplied authorization fields.
        request = replace(
            authorization,
            action=proposal.kind,
            resource=f"calendar:{proposal.calendar_id}",
        )
        decision = self._guard.authorize(request)

        if not decision.allowed:
            return CalendarActionResponse(guard=decision, execution=None)

        durable = DurableCalendarCreate(
            operation_id=operation_id,
            proposal=proposal,
            authorization=AuthorizationEvidence(
                policy_version=decision.policy_version,
                matched_rule_ids=decision.matched_rule_ids,
            ),
        )
        return CalendarActionResponse(
            guard=decision,
            execution=self._durable_actions.create_calendar_event(durable),
        )


class ConflictKind(str, Enum):
    TIME_OVERLAP = "time_overlap"
    TRAVEL_TIME = "travel_time"


@dataclass(frozen=True, slots=True)
class SchedulingConflict:
    kind: ConflictKind
    event_id: str
    available_gap: timedelta | None = None
    required_travel: timedelta | None = None
    travel_source: str | None = None


class CalendarConflictChecker:
    """Conflict logic over calendar data whose read authority was established."""

    def __init__(self, travel_time: TravelTimePort) -> None:
        self._travel_time = travel_time

    def check(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        existing_events: Sequence[CalendarEvent],
    ) -> tuple[SchedulingConflict, ...]:
        conflicts: list[SchedulingConflict] = []

        for event in existing_events:
            if proposal.start < event.end and proposal.end > event.start:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TIME_OVERLAP,
                        event_id=event.event_id,
                    )
                )
                continue

            if not proposal.location or not event.location:
                continue

            if event.end <= proposal.start:
                available = proposal.start - event.end
                estimate = self._travel_time.estimate(
                    origin=event.location,
                    destination=proposal.location,
                )
            elif proposal.end <= event.start:
                available = event.start - proposal.end
                estimate = self._travel_time.estimate(
                    origin=proposal.location,
                    destination=event.location,
                )
            else:
                continue

            if estimate.duration > available:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TRAVEL_TIME,
                        event_id=event.event_id,
                        available_gap=available,
                        required_travel=estimate.duration,
                        travel_source=estimate.source,
                    )
                )

        return tuple(conflicts)


def render_calendar_action_response(
    proposal: CreateCalendarEventProposal,
    response: CalendarActionResponse,
) -> str:
    """Small deterministic response surface for the first vertical slice."""

    if not response.guard.allowed:
        return "I did not create the calendar event because it is not authorized."

    assert response.execution is not None
    status = response.execution.business.status

    if status is BusinessOutcomeStatus.COMMITTED:
        return f"Created the calendar event: {proposal.title}."
    if status is BusinessOutcomeStatus.FAILED:
        if response.execution.provider.error_code == "provider_not_recoverable":
            return (
                f"I did not attempt to create the calendar event: {proposal.title}. "
                "This calendar provider cannot safely recover from a retry."
            )
        return f"I could not create the calendar event: {proposal.title}."
    return (
        f"I cannot confirm whether the calendar event was created: {proposal.title}. "
        "I will not retry it blindly."
    )
