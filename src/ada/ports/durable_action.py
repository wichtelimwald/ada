from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ada.core.action_outcomes import (
    ActionExecutionResult,
    AuthorizationEvidence,
    OperationId,
)
from ada.core.actions import (
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    UpdateCalendarEventProposal,
)


@dataclass(frozen=True, slots=True)
class DurableCalendarCreate:
    """Minimal typed envelope for one authorized calendar create."""

    operation_id: OperationId
    proposal: CreateCalendarEventProposal
    authorization: AuthorizationEvidence


@dataclass(frozen=True, slots=True)
class DurableCalendarUpdate:
    """Minimal typed envelope for one authorized calendar update."""

    operation_id: OperationId
    proposal: UpdateCalendarEventProposal
    authorization: AuthorizationEvidence


@dataclass(frozen=True, slots=True)
class DurableCalendarCancel:
    """Minimal typed envelope for one authorized calendar cancel."""

    operation_id: OperationId
    proposal: CancelCalendarEventProposal
    authorization: AuthorizationEvidence


class DurableActionPort(Protocol):
    """Replaceable durable-execution boundary owned by Ada."""

    def create_calendar_event(
        self,
        request: DurableCalendarCreate,
    ) -> ActionExecutionResult:
        """Execute one authorized create with durable recovery semantics."""

    def update_calendar_event(
        self,
        request: DurableCalendarUpdate,
    ) -> ActionExecutionResult:
        """Execute one authorized update with durable recovery semantics."""

    def cancel_calendar_event(
        self,
        request: DurableCalendarCancel,
    ) -> ActionExecutionResult:
        """Execute one authorized cancel with durable recovery semantics."""
