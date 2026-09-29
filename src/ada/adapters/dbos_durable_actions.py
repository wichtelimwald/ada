from __future__ import annotations

from dbos import DBOS, DBOSConfiguredInstance, SetWorkflowID

from ada.core.action_outcomes import (
    ActionExecutionResult,
    OperationIdentityConflictError,
    ProviderCapability,
    ProviderOutcome,
    ProviderOutcomeStatus,
    business_outcome_from_provider,
)
from ada.core.actions import (
    calendar_cancel_action_binding,
    calendar_create_action_binding,
    calendar_update_action_binding,
)
from ada.ports.calendar import (
    CalendarChangeResult,
    CalendarChangeStatus,
    CalendarCreateResult,
    CalendarCreateStatus,
    CalendarPort,
)
from ada.ports.durable_action import (
    DurableCalendarCancel,
    DurableCalendarCreate,
    DurableCalendarUpdate,
)


def _provider_reference(result: CalendarCreateResult) -> str | None:
    """The known provider reference for a ``COMMITTED`` result, if any.

    A verified ``event`` (read-back succeeded) is preferred; otherwise the
    deterministic ``event_ref`` Ada already knows from the write itself
    (ADR-0009 section 6) is enough to record which resource was created --
    it does not require fabricating a provider-owned ``CalendarEvent``.
    """

    if result.event is not None:
        return result.event.event_id
    if result.event_ref is not None:
        return result.event_ref.resource_name
    return None


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
        operation_id = str(request.operation_id)
        action_binding = calendar_create_action_binding(request.proposal)

        # An operation ID is immutable Ada identity, not merely a convenient
        # DBOS deduplication key. Reject any attempt to reuse it for a
        # different action before accepting a durable replay.
        self._assert_workflow_binding(operation_id, action_binding)

        with SetWorkflowID(operation_id):
            result = self._create_calendar_workflow(
                request,
                action_binding=action_binding,
            )

        # The post-check closes the concurrent first-writer race: if two
        # callers first see no workflow and race with different payloads,
        # DBOS stores one durable input. Only the caller whose binding matches
        # that stored input may receive the durable result.
        self._assert_workflow_binding(operation_id, action_binding)
        return result

    def update_calendar_event(
        self,
        request: DurableCalendarUpdate,
    ) -> ActionExecutionResult:
        operation_id = str(request.operation_id)
        action_binding = calendar_update_action_binding(request.proposal)
        self._assert_workflow_binding(operation_id, action_binding)
        with SetWorkflowID(operation_id):
            result = self._update_calendar_workflow(
                request,
                action_binding=action_binding,
            )
        self._assert_workflow_binding(operation_id, action_binding)
        return result

    def cancel_calendar_event(
        self,
        request: DurableCalendarCancel,
    ) -> ActionExecutionResult:
        operation_id = str(request.operation_id)
        action_binding = calendar_cancel_action_binding(request.proposal)
        self._assert_workflow_binding(operation_id, action_binding)
        with SetWorkflowID(operation_id):
            result = self._cancel_calendar_workflow(
                request,
                action_binding=action_binding,
            )
        self._assert_workflow_binding(operation_id, action_binding)
        return result

    def _assert_workflow_binding(
        self,
        operation_id: str,
        expected_binding: str,
    ) -> None:
        status = DBOS.get_workflow_status(operation_id)
        if status is None:
            return

        stored_input = status.input
        stored_binding: object | None = None
        if isinstance(stored_input, dict):
            kwargs = stored_input.get("kwargs")
            if isinstance(kwargs, dict):
                stored_binding = kwargs.get("action_binding")

        if stored_binding != expected_binding:
            raise OperationIdentityConflictError(
                "operation_id is already bound to different action metadata"
            )

    @DBOS.workflow()
    def _create_calendar_workflow(
        self,
        request: DurableCalendarCreate,
        *,
        action_binding: str,
    ) -> ActionExecutionResult:
        del action_binding  # persisted DBOS identity evidence; semantics are in Ada
        capability = self._calendar.create_capability

        # A provider with neither idempotency nor reconciliation is not safe
        # for automatic durable execution. Until Ada has an explicit at-most-
        # once bridge for such providers, fail closed rather than risk a
        # duplicate real-world effect during workflow recovery.
        if capability is ProviderCapability.NONE:
            provider = ProviderOutcome(
                status=ProviderOutcomeStatus.FAILED,
                error_code="provider_not_recoverable",
            )
            return ActionExecutionResult(
                operation_id=request.operation_id,
                provider=provider,
                business=business_outcome_from_provider(provider),
            )

        return self._create_calendar_step(request)

    @DBOS.workflow()
    def _update_calendar_workflow(
        self,
        request: DurableCalendarUpdate,
        *,
        action_binding: str,
    ) -> ActionExecutionResult:
        del action_binding  # persisted DBOS identity evidence
        if self._calendar.update_capability is ProviderCapability.NONE:
            return self._failed(request, "provider_not_recoverable")
        return self._update_calendar_step(request)

    @DBOS.workflow()
    def _cancel_calendar_workflow(
        self,
        request: DurableCalendarCancel,
        *,
        action_binding: str,
    ) -> ActionExecutionResult:
        del action_binding  # persisted DBOS identity evidence
        if self._calendar.cancel_capability is ProviderCapability.NONE:
            return self._failed(request, "provider_not_recoverable")
        return self._cancel_calendar_step(request)

    @DBOS.step()
    def _update_calendar_step(
        self,
        request: DurableCalendarUpdate,
    ) -> ActionExecutionResult:
        operation_id = str(request.operation_id)
        # The adapter reconciles by re-reading before it writes, so a DBOS
        # replay after a provider commit finds the operation marker instead of
        # reporting a conflict against its own write.
        result = self._calendar.update_event(
            request.proposal, operation_id=operation_id
        )
        if result.status is CalendarChangeStatus.NOT_APPLIED:
            # Provably unchanged base: retry once with the same precondition.
            result = self._calendar.update_event(
                request.proposal, operation_id=operation_id
            )
        return self._change_result(request, result)

    @DBOS.step()
    def _cancel_calendar_step(
        self,
        request: DurableCalendarCancel,
    ) -> ActionExecutionResult:
        operation_id = str(request.operation_id)
        result = self._calendar.cancel_event(
            request.proposal, operation_id=operation_id
        )
        if result.status is CalendarChangeStatus.NOT_APPLIED:
            result = self._calendar.cancel_event(
                request.proposal, operation_id=operation_id
            )
        return self._change_result(request, result)

    def _change_result(
        self,
        request: DurableCalendarUpdate | DurableCalendarCancel,
        result: CalendarChangeResult,
    ) -> ActionExecutionResult:
        """Map an update/cancel result without a stronger claim than its
        evidence. A conflict or an absent event is a confirmed non-commit of
        *Ada's* effect and is told apart by ``error_code``."""

        status = result.status
        if status is CalendarChangeStatus.COMMITTED:
            event_ref = result.event_ref or request.proposal.event_ref
            return self._committed(request, event_ref.resource_name)
        if status is CalendarChangeStatus.AMBIGUOUS:
            return self._ambiguous(
                request, result.error_code or "provider_outcome_ambiguous"
            )
        if status is CalendarChangeStatus.NOT_APPLIED:
            return self._ambiguous(request, "retry_exhausted")
        return self._failed(
            request, result.error_code or f"provider_{status.value}"
        )

    @staticmethod
    def _failed(
        request: DurableCalendarCreate | DurableCalendarUpdate | DurableCalendarCancel,
        error_code: str,
    ) -> ActionExecutionResult:
        provider = ProviderOutcome(
            status=ProviderOutcomeStatus.FAILED,
            error_code=error_code,
        )
        return ActionExecutionResult(
            operation_id=request.operation_id,
            provider=provider,
            business=business_outcome_from_provider(provider),
        )

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
            reference = _provider_reference(result)
            if reference is None:
                return self._ambiguous(request, "provider_missing_reference")
            return self._committed(request, reference)

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
            if retry.status is CalendarCreateStatus.COMMITTED:
                reference = _provider_reference(retry)
                if reference is not None:
                    return self._committed(request, reference)
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
        request: DurableCalendarCreate | DurableCalendarUpdate | DurableCalendarCancel,
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
        request: DurableCalendarCreate | DurableCalendarUpdate | DurableCalendarCancel,
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
