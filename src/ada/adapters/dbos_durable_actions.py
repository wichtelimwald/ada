from __future__ import annotations

from dbos import DBOS, DBOSConfiguredInstance, SetWorkflowID

from ada.core.action_outcomes import (
    ActionExecutionResult,
    ProviderCapability,
    ProviderOutcome,
    ProviderOutcomeStatus,
    business_outcome_from_provider,
)
from ada.ports.calendar import CalendarCreateStatus, CalendarPort
from ada.ports.durable_action import DurableCalendarCreate


@DBOS.dbos_class()
class DBOSDurableCalendarActions(DBOSConfiguredInstance):
    """DBOS-backed durable execution for the first calendar action slice.

    The configured calendar instance must exist before DBOS is launched so
    workflow recovery can resolve the same provider adapter after restart.
    """

    def __init__(
        self,
        calendar: CalendarPort,
        *,
        instance_name: str = "calendar-actions",
    ) -> None:
        self._calendar = calendar
        super().__init__(instance_name)

    def create_calendar_event(
        self,
        request: DurableCalendarCreate,
    ) -> ActionExecutionResult:
        with SetWorkflowID(str(request.operation_id)):
            return self._create_calendar_workflow(request)

    @DBOS.workflow()
    def _create_calendar_workflow(
        self,
        request: DurableCalendarCreate,
    ) -> ActionExecutionResult:
        capability = self._calendar.create_capability

        # A provider with neither idempotency nor reconciliation is not safe
        # for automatic durable execution. Until Ada has an explicit at-most-
        # once bridge for such providers, fail closed rather than risk a
        # duplicate real-world effect during workflow recovery.
        if capability is ProviderCapability.NONE:
            return self._ambiguous(request, "provider_not_recoverable")

        return self._create_calendar_step(request)

    @DBOS.step()
    def _create_calendar_step(
        self,
        request: DurableCalendarCreate,
    ) -> ActionExecutionResult:
        capability = self._calendar.create_capability
        operation_id = str(request.operation_id)

        # Reconcile before a write. On DBOS recovery this is what closes the
        # provider-commit / local-checkpoint crash window.
        if capability is ProviderCapability.RECONCILABLE:
            existing = self._calendar.reconcile_create(operation_id=operation_id)
            if existing is not None:
                return self._committed(request, existing.event_id)

        result = self._calendar.create_event(
            request.proposal,
            operation_id=operation_id,
        )

        if result.status is CalendarCreateStatus.COMMITTED:
            if result.event is None:
                return self._ambiguous(request, "provider_missing_reference")
            return self._committed(request, result.event.event_id)

        if result.status is CalendarCreateStatus.REJECTED:
            provider = ProviderOutcome(
                status=ProviderOutcomeStatus.FAILED,
                error_code=result.error_code or "provider_rejected",
            )
            return ActionExecutionResult(
                operation_id=request.operation_id,
                provider=provider,
                business=business_outcome_from_provider(provider),
            )

        if capability is ProviderCapability.RECONCILABLE:
            existing = self._calendar.reconcile_create(operation_id=operation_id)
            if existing is not None:
                return self._committed(request, existing.event_id)

        if capability is ProviderCapability.IDEMPOTENT:
            retry = self._calendar.create_event(
                request.proposal,
                operation_id=operation_id,
            )
            if retry.status is CalendarCreateStatus.COMMITTED and retry.event:
                return self._committed(request, retry.event.event_id)
            if retry.status is CalendarCreateStatus.REJECTED:
                provider = ProviderOutcome(
                    status=ProviderOutcomeStatus.FAILED,
                    error_code=retry.error_code or "provider_rejected",
                )
                return ActionExecutionResult(
                    operation_id=request.operation_id,
                    provider=provider,
                    business=business_outcome_from_provider(provider),
                )

        return self._ambiguous(
            request,
            result.error_code or "provider_outcome_ambiguous",
        )

    @staticmethod
    def _committed(
        request: DurableCalendarCreate,
        provider_reference: str,
    ) -> ActionExecutionResult:
        provider = ProviderOutcome(
            status=ProviderOutcomeStatus.COMMITTED,
            provider_reference=provider_reference,
        )
        return ActionExecutionResult(
            operation_id=request.operation_id,
            provider=provider,
            business=business_outcome_from_provider(provider),
        )

    @staticmethod
    def _ambiguous(
        request: DurableCalendarCreate,
        error_code: str,
    ) -> ActionExecutionResult:
        provider = ProviderOutcome(
            status=ProviderOutcomeStatus.AMBIGUOUS,
            error_code=error_code,
        )
        return ActionExecutionResult(
            operation_id=request.operation_id,
            provider=provider,
            business=business_outcome_from_provider(provider),
        )
