from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dbos import DBOS, DBOSConfig

from ada.adapters.cedar_guard import CedarGuard
from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.adapters.in_memory_calendar import InMemoryCalendarAdapter
from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.application.calendar_actions import (
    CalendarActionService,
    CalendarConflictChecker,
    ConflictKind,
    render_calendar_action_response,
)
from ada.core.action_outcomes import (
    AuthorizationEvidence,
    BusinessOutcomeStatus,
    OperationId,
    OperationIdentityConflictError,
    ProviderCapability,
    ProviderOutcomeStatus,
)
from ada.core.actions import (
    CalendarProposalValidationError,
    CreateCalendarEventProposal,
)
from ada.core.authorization import (
    AuthenticationAssurance,
    AuthorizationRequest,
    InstructionProvenance,
)
from ada.ports.agent_runtime import AgentRequest
from ada.ports.calendar import CalendarEvent
from ada.ports.durable_action import DurableCalendarCreate
from ada.ports.travel_time import TravelEstimate


NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)

CALENDAR_GRANT = """
@id("grant-family-calendar")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.create",
    resource == AdaResource::"calendar:family"
)
when {
    context.provenance == "direct" &&
    context.assurance == "local_trusted"
};
"""


class FixedTravelTime:
    def __init__(self, minutes: int) -> None:
        self._duration = timedelta(minutes=minutes)

    def estimate(self, *, origin: str, destination: str) -> TravelEstimate:
        return TravelEstimate(
            duration=self._duration,
            source=f"synthetic:{origin}->{destination}",
        )


def proposal(
    *,
    title: str = "Parent-teacher meeting",
    start: datetime | None = None,
    end: datetime | None = None,
    calendar_id: str = "family",
    location: str | None = "School North",
) -> CreateCalendarEventProposal:
    return CreateCalendarEventProposal(
        title=title,
        start=start or datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        end=end or datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc),
        calendar_id=calendar_id,
        location=location,
    )


def authorization() -> AuthorizationRequest:
    return AuthorizationRequest(
        actor="guardian-a",
        action="ignored-by-service",
        resource="ignored-by-service",
        data_subjects=("child-a",),
        audience="family",
        purpose="family-coordination",
        provenance=InstructionProvenance.DIRECT,
        channel="local-chat",
        assurance=AuthenticationAssurance.LOCAL_TRUSTED,
    )


class DurableCalendarVerticalSliceTests(unittest.TestCase):
    _counter = 0

    def setUp(self) -> None:
        type(self)._counter += 1
        self.tmp = tempfile.TemporaryDirectory()
        DBOS.destroy()
        config: DBOSConfig = {
            "name": f"ada-test-{self._counter}",
            "application_version": "test",
            "run_admin_server": False,
            "log_level": "WARNING",
            "console_log_level": "WARNING",
            "system_database_url": (
                f"sqlite:///{Path(self.tmp.name) / 'dbos.sqlite'}"
            ),
        }
        DBOS(config=config)

    def tearDown(self) -> None:
        DBOS.destroy()
        self.tmp.cleanup()

    def launch_adapter(
        self,
        calendar: InMemoryCalendarAdapter,
    ) -> DBOSDurableCalendarActions:
        adapter = DBOSDurableCalendarActions(
            calendar,
            instance_name=f"calendar-actions-{self._counter}",
        )
        DBOS.launch()
        return adapter

    def guard(self, policy: str = CALENDAR_GRANT) -> CedarGuard:
        return CedarGuard(
            policy,
            policy_version="test-policy-v1",
            clock=lambda: NOW,
        )

    def test_typed_pydantic_result_reaches_guard_and_durable_calendar(self) -> None:
        expected = proposal()

        class FakeResult:
            output = expected

        class FakeAgent:
            def run_sync(self, prompt: str) -> FakeResult:
                self.prompt = prompt
                return FakeResult()

        runtime = PydanticAIRuntime(FakeAgent())
        agent_response = runtime.run(
            AgentRequest(
                text=(
                    "Please add the forwarded parent-teacher appointment "
                    "to the family calendar."
                )
            )
        )
        self.assertEqual(agent_response.proposals, (expected,))

        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )

        response = service.create_event(
            agent_response.proposals[0],
            operation_id=OperationId("op-school-appointment-1"),
            authorization=authorization(),
        )

        self.assertTrue(response.guard.allowed)
        self.assertIsNotNone(response.execution)
        assert response.execution is not None
        self.assertEqual(
            response.execution.provider.status,
            ProviderOutcomeStatus.COMMITTED,
        )
        self.assertEqual(
            response.execution.business.status,
            BusinessOutcomeStatus.COMMITTED,
        )
        self.assertEqual(calendar.create_attempts, 1)
        self.assertEqual(
            render_calendar_action_response(expected, response),
            "Created the calendar event: Parent-teacher meeting.",
        )

    def test_same_operation_id_reuses_dbos_result_without_duplicate(self) -> None:
        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )
        operation_id = OperationId("op-idempotent-replay")

        first = service.create_event(
            proposal(),
            operation_id=operation_id,
            authorization=authorization(),
        )
        second = service.create_event(
            proposal(),
            operation_id=operation_id,
            authorization=authorization(),
        )

        self.assertEqual(first.execution, second.execution)
        self.assertEqual(calendar.create_attempts, 1)

    def test_invalid_calendar_proposals_stop_before_provider_execution(self) -> None:
        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        class GuardMustNotBeCalled:
            def authorize(self, request: AuthorizationRequest) -> None:
                del request
                raise AssertionError("invalid proposal reached AdaGuard")

        service = CalendarActionService(
            guard=GuardMustNotBeCalled(),
            durable_actions=durable,
        )
        start = datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc)

        invalid_proposals = (
            proposal(title="   "),
            proposal(calendar_id="   "),
            proposal(start=start, end=start),
            proposal(
                start=datetime(2026, 10, 12, 16, 0),
                end=datetime(2026, 10, 12, 16, 30),
            ),
        )

        for index, invalid in enumerate(invalid_proposals):
            with self.subTest(index=index):
                with self.assertRaises(CalendarProposalValidationError):
                    service.create_event(
                        invalid,
                        operation_id=OperationId(f"op-invalid-{index}"),
                        authorization=authorization(),
                    )

        self.assertEqual(calendar.create_attempts, 0)
        self.assertEqual(calendar.effect_count, 0)

    def test_concurrent_first_writer_rejects_mismatched_loser(self) -> None:
        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        operation_id = OperationId("op-concurrent-binding")
        evidence = AuthorizationEvidence(
            policy_version="test-policy-v1",
            matched_rule_ids=("grant-family-calendar",),
        )
        requests = (
            DurableCalendarCreate(
                operation_id=operation_id,
                proposal=proposal(title="Concurrent appointment A"),
                authorization=evidence,
            ),
            DurableCalendarCreate(
                operation_id=operation_id,
                proposal=proposal(title="Concurrent appointment B"),
                authorization=evidence,
            ),
        )

        # Force both callers to complete the initial binding lookup before
        # either can proceed to DBOS workflow creation. This deterministically
        # exercises the post-check rather than merely the normal pre-check.
        entered = threading.Barrier(2)
        checked = threading.Barrier(2)
        seen_threads: set[int] = set()
        seen_lock = threading.Lock()
        original_assert = DBOSDurableCalendarActions._assert_workflow_binding

        def coordinated_assert(
            instance: DBOSDurableCalendarActions,
            candidate_operation_id: str,
            expected_binding: str,
        ) -> None:
            thread_id = threading.get_ident()
            with seen_lock:
                first_check = thread_id not in seen_threads
                if first_check:
                    seen_threads.add(thread_id)

            if first_check:
                entered.wait(timeout=5)
                original_assert(
                    instance,
                    candidate_operation_id,
                    expected_binding,
                )
                checked.wait(timeout=5)
                return

            original_assert(
                instance,
                candidate_operation_id,
                expected_binding,
            )

        results = []
        conflicts = []
        with patch.object(
            DBOSDurableCalendarActions,
            "_assert_workflow_binding",
            new=coordinated_assert,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(durable.create_calendar_event, request)
                    for request in requests
                ]
                for future in futures:
                    try:
                        results.append(future.result(timeout=15))
                    except OperationIdentityConflictError as exc:
                        conflicts.append(exc)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(
            results[0].provider.status,
            ProviderOutcomeStatus.COMMITTED,
        )
        self.assertEqual(calendar.effect_count, 1)

    def test_same_operation_id_rejects_different_action_payload(self) -> None:
        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )
        operation_id = OperationId("op-bound-action")

        first = service.create_event(
            proposal(),
            operation_id=operation_id,
            authorization=authorization(),
        )
        self.assertIsNotNone(first.execution)

        with self.assertRaises(OperationIdentityConflictError):
            service.create_event(
                proposal(title="Different appointment"),
                operation_id=operation_id,
                authorization=authorization(),
            )

        self.assertEqual(calendar.create_attempts, 1)
        self.assertEqual(calendar.effect_count, 1)

    def test_preexisting_provider_commit_is_reconciled_without_create(self) -> None:
        calendar = InMemoryCalendarAdapter()
        operation_id = OperationId("op-crash-window")

        # Unit-level reconciliation check. The process-level hard-crash path
        # is covered separately in test_durable_calendar_crash_recovery.py.
        direct = calendar.create_event(
            proposal(),
            operation_id=str(operation_id),
        )
        self.assertIsNotNone(direct.event)
        self.assertEqual(calendar.create_attempts, 1)

        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )
        recovered = service.create_event(
            proposal(),
            operation_id=operation_id,
            authorization=authorization(),
        )

        assert recovered.execution is not None
        self.assertEqual(
            recovered.execution.provider.status,
            ProviderOutcomeStatus.COMMITTED,
        )
        self.assertEqual(calendar.create_attempts, 1)

    def test_ambiguous_provider_response_reconciles_existing_commit(self) -> None:
        calendar = InMemoryCalendarAdapter(ambiguous_after_commit_once=True)
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )

        response = service.create_event(
            proposal(),
            operation_id=OperationId("op-response-lost-after-commit"),
            authorization=authorization(),
        )

        assert response.execution is not None
        self.assertEqual(
            response.execution.provider.status,
            ProviderOutcomeStatus.COMMITTED,
        )
        self.assertEqual(calendar.create_attempts, 1)

    def test_confirmed_provider_failure_maps_to_failed_business_outcome(self) -> None:
        calendar = InMemoryCalendarAdapter(reject_creates=True)
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )

        response = service.create_event(
            proposal(),
            operation_id=OperationId("op-provider-rejected"),
            authorization=authorization(),
        )

        assert response.execution is not None
        self.assertEqual(
            response.execution.provider.status,
            ProviderOutcomeStatus.FAILED,
        )
        self.assertEqual(
            response.execution.business.status,
            BusinessOutcomeStatus.FAILED,
        )
        self.assertEqual(calendar.create_attempts, 1)
        self.assertEqual(calendar.effect_count, 0)
        self.assertEqual(
            render_calendar_action_response(proposal(), response),
            "I could not create the calendar event: Parent-teacher meeting.",
        )

    def test_idempotent_provider_retry_commits_one_external_effect(self) -> None:
        calendar = InMemoryCalendarAdapter(
            create_capability=ProviderCapability.IDEMPOTENT,
            ambiguous_after_commit_once=True,
        )
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )

        response = service.create_event(
            proposal(),
            operation_id=OperationId("op-idempotent-provider-retry"),
            authorization=authorization(),
        )

        assert response.execution is not None
        self.assertEqual(
            response.execution.provider.status,
            ProviderOutcomeStatus.COMMITTED,
        )
        self.assertEqual(
            response.execution.business.status,
            BusinessOutcomeStatus.COMMITTED,
        )
        self.assertEqual(calendar.create_attempts, 2)
        self.assertEqual(calendar.effect_count, 1)

    def test_provider_without_duplicate_safety_is_not_attempted(self) -> None:
        calendar = InMemoryCalendarAdapter(
            create_capability=ProviderCapability.NONE,
        )
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(),
            durable_actions=durable,
        )

        response = service.create_event(
            proposal(),
            operation_id=OperationId("op-unsafe-provider"),
            authorization=authorization(),
        )

        assert response.execution is not None
        self.assertEqual(
            response.execution.provider.status,
            ProviderOutcomeStatus.FAILED,
        )
        self.assertEqual(
            response.execution.business.status,
            BusinessOutcomeStatus.FAILED,
        )
        self.assertEqual(
            response.execution.provider.error_code,
            "provider_not_recoverable",
        )
        self.assertEqual(calendar.create_attempts, 0)
        self.assertEqual(
            render_calendar_action_response(proposal(), response),
            (
                "I did not attempt to create the calendar event: "
                "Parent-teacher meeting. "
                "This calendar provider cannot safely recover from a retry."
            ),
        )

    def test_guard_denial_produces_zero_provider_effects(self) -> None:
        calendar = InMemoryCalendarAdapter()
        durable = self.launch_adapter(calendar)
        service = CalendarActionService(
            guard=self.guard(policy=""),
            durable_actions=durable,
        )

        response = service.create_event(
            proposal(),
            operation_id=OperationId("op-denied"),
            authorization=authorization(),
        )

        self.assertFalse(response.guard.allowed)
        self.assertIsNone(response.execution)
        self.assertEqual(calendar.create_attempts, 0)

    def test_conflict_checker_detects_travel_time_gap(self) -> None:
        checker = CalendarConflictChecker(FixedTravelTime(minutes=25))
        candidate = proposal(
            start=datetime(2026, 10, 12, 15, 40, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 16, 10, tzinfo=timezone.utc),
            location="Location B",
        )
        existing = CalendarEvent(
            event_id="existing-a",
            title="School appointment",
            start=datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 15, 30, tzinfo=timezone.utc),
            calendar_id="family",
            location="Location A",
        )

        conflicts = checker.check(candidate, existing_events=(existing,))

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].kind, ConflictKind.TRAVEL_TIME)
        self.assertEqual(conflicts[0].available_gap, timedelta(minutes=10))
        self.assertEqual(conflicts[0].required_travel, timedelta(minutes=25))
        self.assertEqual(
            conflicts[0].travel_source,
            "synthetic:Location A->Location B",
        )

    def test_conflict_checker_detects_reverse_direction_travel_gap(self) -> None:
        checker = CalendarConflictChecker(FixedTravelTime(minutes=25))
        candidate = proposal(
            start=datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 15, 30, tzinfo=timezone.utc),
            location="Location B",
        )
        existing = CalendarEvent(
            event_id="existing-after",
            title="Later appointment",
            start=datetime(2026, 10, 12, 15, 40, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 16, 10, tzinfo=timezone.utc),
            calendar_id="family",
            location="Location A",
        )

        conflicts = checker.check(candidate, existing_events=(existing,))

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].kind, ConflictKind.TRAVEL_TIME)
        self.assertEqual(conflicts[0].available_gap, timedelta(minutes=10))
        self.assertEqual(conflicts[0].required_travel, timedelta(minutes=25))
        self.assertEqual(
            conflicts[0].travel_source,
            "synthetic:Location B->Location A",
        )

    def test_conflict_checker_detects_direct_overlap_without_location_data(self) -> None:
        checker = CalendarConflictChecker(FixedTravelTime(minutes=25))
        candidate = proposal(
            start=datetime(2026, 10, 12, 15, 15, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
            location="Location B",
        )
        existing = CalendarEvent(
            event_id="existing-overlap",
            title="Existing appointment",
            start=datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 12, 15, 30, tzinfo=timezone.utc),
            calendar_id="family",
            location=None,
        )

        conflicts = checker.check(candidate, existing_events=(existing,))

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].kind, ConflictKind.TIME_OVERLAP)


if __name__ == "__main__":
    unittest.main()
