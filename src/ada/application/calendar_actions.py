from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from enum import Enum
from typing import Collection, Mapping, Sequence

from ada.core.action_outcomes import (
    ActionExecutionResult,
    AuthorizationEvidence,
    BusinessOutcomeStatus,
    OperationId,
)
from ada.core.actions import (
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    UpdateCalendarEventProposal,
    validate_calendar_cancel_proposal,
    validate_calendar_create_proposal,
    validate_calendar_update_proposal,
)
from ada.core.authorization import AuthorizationRequest, GuardDecision
from ada.ports.calendar import CalendarBusyInterval, CalendarEvent
from ada.ports.durable_action import (
    DurableActionPort,
    DurableCalendarCancel,
    DurableCalendarCreate,
    DurableCalendarUpdate,
)
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


    def update_event(
        self,
        proposal: UpdateCalendarEventProposal,
        *,
        operation_id: OperationId,
        authorization: AuthorizationRequest,
    ) -> CalendarActionResponse:
        validate_calendar_update_proposal(proposal)
        decision = self._authorize(
            proposal.kind, proposal.event_ref.calendar_id, authorization
        )
        if not decision.allowed:
            return CalendarActionResponse(guard=decision, execution=None)

        durable = DurableCalendarUpdate(
            operation_id=operation_id,
            proposal=proposal,
            authorization=_evidence(decision),
        )
        return CalendarActionResponse(
            guard=decision,
            execution=self._durable_actions.update_calendar_event(durable),
        )

    def cancel_event(
        self,
        proposal: CancelCalendarEventProposal,
        *,
        operation_id: OperationId,
        authorization: AuthorizationRequest,
    ) -> CalendarActionResponse:
        validate_calendar_cancel_proposal(proposal)
        decision = self._authorize(
            proposal.kind, proposal.event_ref.calendar_id, authorization
        )
        if not decision.allowed:
            return CalendarActionResponse(guard=decision, execution=None)

        durable = DurableCalendarCancel(
            operation_id=operation_id,
            proposal=proposal,
            authorization=_evidence(decision),
        )
        return CalendarActionResponse(
            guard=decision,
            execution=self._durable_actions.cancel_calendar_event(durable),
        )

    def _authorize(
        self,
        action: str,
        calendar_id: str,
        authorization: AuthorizationRequest,
    ) -> GuardDecision:
        # Privileged action/resource come from the typed proposal, never from
        # model/tool-supplied authorization fields.
        return self._guard.authorize(
            replace(
                authorization,
                action=action,
                resource=f"calendar:{calendar_id}",
            )
        )


def _evidence(decision: GuardDecision) -> AuthorizationEvidence:
    return AuthorizationEvidence(
        policy_version=decision.policy_version,
        matched_rule_ids=decision.matched_rule_ids,
    )


def availability_for_conflicts(
    events: Sequence[CalendarEvent],
    *,
    relevant_calendar_ids: Collection[str],
    registered_places: Mapping[str, str],
) -> tuple[CalendarBusyInterval, ...]:
    """Project authorized calendar reads into availability-only inputs.

    The caller must choose relevant calendars from trusted user/audience
    configuration, not from a model request. A family calendar is included
    when it affects the people being scheduled. Provider titles, locations
    and event identifiers do not enter the resulting conflict inputs.
    CalDAV already expands recurring occurrences before this projection.
    """

    allowed = frozenset(relevant_calendar_ids)
    intervals: list[CalendarBusyInterval] = []
    for event in events:
        if not event.busy or event.calendar_id not in allowed:
            continue
        intervals.append(
            CalendarBusyInterval(
                slot_id=f"slot-{len(intervals) + 1}",
                calendar_id=event.calendar_id,
                start=event.start,
                end=event.end,
                place_key=(
                    registered_places.get(event.location)
                    if event.location is not None
                    else None
                ),
            )
        )
    return tuple(intervals)


class ConflictKind(str, Enum):
    TIME_OVERLAP = "time_overlap"
    TRAVEL_TIME = "travel_time"
    TRAVEL_UNKNOWN = "travel_unknown"


@dataclass(frozen=True, slots=True)
class SchedulingConflict:
    kind: ConflictKind
    # An ephemeral availability token; not a provider ID or event detail.
    slot_id: str
    available_gap: timedelta | None = None
    required_travel: timedelta | None = None
    travel_source: str | None = None


class CalendarConflictChecker:
    """Check one affected person's authorized busy schedule.

    The caller must include shared/family intervals that affect this person.
    For a family event, invoke the checker separately for each affected
    person's schedule; combining unrelated people's slots can hide a real
    nearest-neighbor travel conflict. Authorization and audience selection
    remain the caller's trusted responsibility.
    """

    def __init__(self, travel_time: TravelTimePort) -> None:
        self._travel_time = travel_time

    def check(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        existing_events: Sequence[CalendarBusyInterval],
        candidate_place_key: str | None = None,
    ) -> tuple[SchedulingConflict, ...]:
        conflicts: list[SchedulingConflict] = []

        # All overlapping appointments matter, but travel between the new
        # appointment and nonadjacent ones does not. Select the immediate
        # predecessor(s) and successor(s) in this person's schedule.
        preceding: list[CalendarBusyInterval] = []
        following: list[CalendarBusyInterval] = []
        for event in existing_events:
            if proposal.start < event.end and proposal.end > event.start:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TIME_OVERLAP,
                        slot_id=event.slot_id,
                    )
                )
            elif event.end <= proposal.start:
                preceding.append(event)
            elif proposal.end <= event.start:
                following.append(event)

        adjacent: list[tuple[CalendarBusyInterval, timedelta, str | None, str | None]] = []
        if preceding:
            nearest_end = max(event.end for event in preceding)
            for event in preceding:
                if event.end == nearest_end:
                    adjacent.append(
                        (
                            event,
                            proposal.start - event.end,
                            event.place_key,
                            candidate_place_key,
                        )
                    )
        if following:
            nearest_start = min(event.start for event in following)
            for event in following:
                if event.start == nearest_start:
                    adjacent.append(
                        (
                            event,
                            event.start - proposal.end,
                            candidate_place_key,
                            event.place_key,
                        )
                    )

        for event, available, origin, destination in adjacent:
            if origin is None or destination is None:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TRAVEL_UNKNOWN,
                        slot_id=event.slot_id,
                        available_gap=available,
                        travel_source="place_not_registered",
                    )
                )
                continue

            estimate = self._travel_time.estimate(
                origin=origin, destination=destination
            )
            if estimate.duration is None:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TRAVEL_UNKNOWN,
                        slot_id=event.slot_id,
                        available_gap=available,
                        travel_source=estimate.source,
                    )
                )
            elif estimate.duration > available:
                conflicts.append(
                    SchedulingConflict(
                        kind=ConflictKind.TRAVEL_TIME,
                        slot_id=event.slot_id,
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


def render_calendar_change_response(
    verb: str,
    response: CalendarActionResponse,
) -> str:
    """Deterministic text for an update/cancel outcome.

    ``verb`` is ``"update"`` or ``"cancel"``. A conflict or an absent event is
    reported as such, never as Ada's own effect.
    """

    if not response.guard.allowed:
        return f"I did not {verb} the calendar event because it is not authorized."

    assert response.execution is not None
    execution = response.execution
    status = execution.business.status
    error_code = execution.provider.error_code

    if status is BusinessOutcomeStatus.COMMITTED:
        return f"I did {verb} the calendar event."
    if status is BusinessOutcomeStatus.AMBIGUOUS:
        if error_code == "event_absent_cause_unknown":
            # The goal state is known; Ada's own effect is not.
            return (
                f"The calendar event no longer exists, but I cannot confirm "
                f"whether my {verb} caused that. I will not retry it blindly."
            )
        if error_code is not None and error_code.endswith("_after_possible_send"):
            return (
                f"I cannot confirm whether my {verb} was applied: an earlier "
                "attempt may already have reached the calendar. I will not "
                "retry it blindly."
            )
        return (
            f"I cannot confirm whether the calendar event was changed by this "
            f"{verb}. I will not retry it blindly."
        )
    if error_code == "version_conflict":
        return (
            f"I did not {verb} the calendar event: it changed after it was "
            "approved. Nothing was overwritten."
        )
    if error_code == "event_absent":
        # Only reported when the absence was observed before any send.
        return "The calendar event no longer exists; I made no change."
    if error_code in (
        "recurring_event_read_only",
        "attendee_event_read_only",
        "all_day_time_change_unsupported",
    ):
        return (
            f"I did not {verb} the calendar event: recurring events, events "
            "with attendees and all-day time changes are read-only for me."
        )
    if error_code == "provider_not_recoverable":
        return (
            f"I did not attempt to {verb} the calendar event. This calendar "
            "provider cannot safely recover from a retry."
        )
    return f"I could not {verb} the calendar event."
