from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ada.core.action_outcomes import (
    ActionExecutionResult,
    AuthorizationEvidence,
    OperationId,
)
from ada.core.actions import CreateCalendarEventProposal


@dataclass(frozen=True, slots=True)
class DurableCalendarCreate:
    """Minimal typed envelope for one authorized calendar create."""

    operation_id: OperationId
    proposal: CreateCalendarEventProposal
    authorization: AuthorizationEvidence


class DurableActionPort(Protocol):
    """Replaceable durable-execution boundary owned by Ada."""

    def create_calendar_event(
        self,
        request: DurableCalendarCreate,
    ) -> ActionExecutionResult:
        """Execute one authorized create with durable recovery semantics."""
