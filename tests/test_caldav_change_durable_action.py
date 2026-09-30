from __future__ import annotations

import dataclasses
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import httpx2
from dbos import DBOS, DBOSConfig

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE, CalDAVProviderProfile
from ada.adapters.cedar_guard import CedarGuard
from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.adapters.in_memory_calendar import InMemoryCalendarAdapter
from ada.application.calendar_actions import (
    CalendarActionService,
    render_calendar_change_response,
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
    CalendarEventChanges,
    CalendarProposalValidationError,
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    EventBaseVersion,
    UpdateCalendarEventProposal,
)
from ada.core.authorization import (
    AuthenticationAssurance,
    AuthorizationRequest,
    InstructionProvenance,
)
from ada.ports.calendar import CalendarEvent, CalendarPort
from ada.ports.durable_action import DurableCalendarCancel, DurableCalendarUpdate
from caldav_test_support import (
    BASE_URL,
    FAKE_AUTH,
    FAMILY_PATH,
    build_fake_server,
    default_family_ref,
)

START = datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc)
END = datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc)

POLICY = """
@id("grant-update")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.update",
    resource == AdaResource::"calendar:family"
)
when { context.provenance == "direct" && context.assurance == "local_trusted" };

@id("grant-cancel")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.cancel",
    resource == AdaResource::"calendar:family"
)
when { context.provenance == "direct" && context.assurance == "local_trusted" };
"""

EVIDENCE = AuthorizationEvidence(
    policy_version="test-policy-v1", matched_rule_ids=("grant-family-calendar",)
)


def authorization(provenance: InstructionProvenance = InstructionProvenance.DIRECT):
    return AuthorizationRequest(
        actor="guardian-a",
        action="ignored-by-service",
        resource="ignored-by-service",
        data_subjects=("child-a",),
        audience="family",
        purpose="family-coordination",
        provenance=provenance,
        channel="local-chat",
        assurance=AuthenticationAssurance.LOCAL_TRUSTED,
    )


class _Base(unittest.TestCase):
    _counter = 0

    def setUp(self) -> None:
        type(self)._counter += 1
        _Base._counter += 1
        self.tmp = tempfile.TemporaryDirectory()
        DBOS.destroy()
        config: DBOSConfig = {
            "name": f"ada-caldav-change-test-{_Base._counter}",
            "application_version": "test",
            "run_admin_server": False,
            "log_level": "WARNING",
            "console_log_level": "WARNING",
            "system_database_url": f"sqlite:///{Path(self.tmp.name) / 'dbos.sqlite'}",
        }
        DBOS(config=config)

    def tearDown(self) -> None:
        DBOS.destroy()
        self.tmp.cleanup()

    def launch(self, calendar: CalendarPort) -> DBOSDurableCalendarActions:
        durable = DBOSDurableCalendarActions(
            calendar, instance_name=f"calendar-actions-change-{_Base._counter}"
        )
        DBOS.launch()
        return durable


class CalDAVChangeDurableTests(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.server = build_fake_server()
        self.requests: list[str] = []

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            self.requests.append(request.method)
            return self.server(request)

        self.profile: CalDAVProviderProfile = IONOS_PROFILE
        self.dispatch = dispatch

    def adapter(self, profile: CalDAVProviderProfile | None = None) -> CalDAVCalendarAdapter:
        calendar = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(default_family_ref(),),
            profile=profile or self.profile,
            transport=httpx2.MockTransport(self.dispatch),
            clock=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        self.addCleanup(calendar.close)
        return calendar

    def seed(self, calendar: CalDAVCalendarAdapter) -> CalendarEvent:
        result = calendar.create_event(
            CreateCalendarEventProposal(
                title="Synthetic dentist",
                start=START,
                end=END,
                calendar_id="family",
                location="Clinic",
            ),
            operation_id="seed",
        )
        assert result.event is not None
        return result.event

    @staticmethod
    def update_request(
        event: CalendarEvent, operation_id: str, title: str = "Moved"
    ) -> DurableCalendarUpdate:
        assert event.event_ref is not None and event.version is not None
        return DurableCalendarUpdate(
            operation_id=OperationId(operation_id),
            proposal=UpdateCalendarEventProposal(
                event_ref=event.event_ref,
                base_version=EventBaseVersion(event.version, event.sequence),
                changes=CalendarEventChanges(title=title),
            ),
            authorization=EVIDENCE,
        )

    @staticmethod
    def cancel_request(event: CalendarEvent, operation_id: str) -> DurableCalendarCancel:
        assert event.event_ref is not None and event.version is not None
        return DurableCalendarCancel(
            operation_id=OperationId(operation_id),
            proposal=CancelCalendarEventProposal(
                event_ref=event.event_ref,
                base_version=EventBaseVersion(event.version, event.sequence),
            ),
            authorization=EVIDENCE,
        )

    def test_update_commits_and_reports_the_resource(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)

        result = durable.update_calendar_event(self.update_request(event, "op-upd"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.COMMITTED)
        self.assertEqual(result.business.status, BusinessOutcomeStatus.COMMITTED)
        assert event.event_ref is not None
        self.assertEqual(result.provider.provider_reference, event.event_ref.resource_name)

    def test_update_after_human_edit_reports_conflict_and_writes_nothing(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        assert event.event_ref is not None
        body = self.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)
        assert body is not None
        self.server.human_edit(
            FAMILY_PATH, event.event_ref.resource_name, body.replace(b"dentist", b"HUMAN")
        )
        durable = self.launch(calendar)

        result = durable.update_calendar_event(self.update_request(event, "op-conflict"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(result.provider.error_code, "version_conflict")
        self.assertEqual(result.business.status, BusinessOutcomeStatus.FAILED)
        self.assertEqual(self.server.conditional_writes, [])
        stored = self.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)
        assert stored is not None
        self.assertIn(b"HUMAN", stored)

    def test_lost_response_after_commit_is_committed_after_reconciliation(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_response_after_commit = 1

        result = durable.update_calendar_event(self.update_request(event, "op-lost"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.COMMITTED)
        self.assertEqual(len(self.server.conditional_writes), 1)

    def test_lost_request_before_commit_is_retried_once_with_the_same_precondition(
        self,
    ) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_before_commit = 1

        result = durable.update_calendar_event(self.update_request(event, "op-retry"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.COMMITTED)
        self.assertEqual(len(self.server.conditional_writes), 2)
        self.assertEqual(len({tag for _, tag in self.server.conditional_writes}), 1)

    def test_repeated_not_applied_is_ambiguous_not_retried_blindly(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_before_commit = 2

        result = durable.update_calendar_event(self.update_request(event, "op-exhaust"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.provider.error_code, "retry_exhausted")
        self.assertEqual(len(self.server.conditional_writes), 2)

    def test_unresolvable_lost_response_is_ambiguous_and_not_retried(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        assert event.event_ref is not None
        durable = self.launch(calendar)
        self.server.lose_write_response_after_commit = 1
        real_get = self.server._get
        edited = {"done": False}

        def get_then_edit(path: str) -> httpx2.Response:
            if not edited["done"] and self.server.conditional_writes:
                edited["done"] = True
                body = self.server.resource_body(
                    FAMILY_PATH, event.event_ref.resource_name  # type: ignore[union-attr]
                )
                assert body is not None
                self.server.human_edit(
                    FAMILY_PATH,
                    event.event_ref.resource_name,  # type: ignore[union-attr]
                    body.replace(b"X-ADA-OPERATION-MARKER", b"X-OTHER"),
                )
            return real_get(path)

        self.server._get = get_then_edit  # type: ignore[method-assign]

        result = durable.update_calendar_event(self.update_request(event, "op-ambig"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.business.status, BusinessOutcomeStatus.AMBIGUOUS)
        self.assertEqual(len(self.server.conditional_writes), 1)

    def test_cancel_commits_and_repeat_reports_absent(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)

        first = durable.cancel_calendar_event(self.cancel_request(event, "op-cancel"))
        again = durable.cancel_calendar_event(self.cancel_request(event, "op-cancel"))
        fresh = durable.cancel_calendar_event(self.cancel_request(event, "op-cancel-2"))

        self.assertEqual(first.provider.status, ProviderOutcomeStatus.COMMITTED)
        # The same operation replays its recorded result: exactly one DELETE.
        self.assertEqual(again, first)
        self.assertEqual(self.requests.count("DELETE"), 1)
        # A new operation on the gone event is "no longer exists", not a
        # fresh effect.
        self.assertEqual(fresh.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(fresh.provider.error_code, "event_absent")
        self.assertEqual(self.requests.count("DELETE"), 1)

    def _after_first_write_attempt(self, action, *, on_get: int) -> None:  # type: ignore[no-untyped-def]
        """Run ``action`` just before the ``on_get``-th read that follows the
        first conditional write attempt (1 = the reconciliation read,
        2 = the retry's pre-read)."""

        real_get = self.server._get
        state = {"seen": 0}

        def get(path: str) -> httpx2.Response:
            if self.server.conditional_writes:
                state["seen"] += 1
                if state["seen"] == on_get:
                    action()
            return real_get(path)

        self.server._get = get  # type: ignore[method-assign]

    def test_update_absent_after_ambiguous_send_is_ambiguous_end_to_end(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_response_after_commit = 1
        self._after_first_write_attempt(
            lambda: self.server._collections[FAMILY_PATH].resources.clear(),
            on_get=1,
        )

        result = durable.update_calendar_event(self.update_request(event, "op-gone"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.provider.error_code, "event_absent_cause_unknown")
        self.assertEqual(result.business.status, BusinessOutcomeStatus.AMBIGUOUS)

    def test_cancel_lost_response_knows_absence_but_reports_no_non_commit(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_response_after_commit = 1

        result = durable.cancel_calendar_event(self.cancel_request(event, "op-cancel-lost"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.provider.error_code, "event_absent_cause_unknown")
        self.assertNotEqual(result.business.summary_code, "provider_non_commit_confirmed")
        self.assertEqual(self.requests.count("DELETE"), 1)

    def test_change_found_while_retrying_after_a_send_is_not_a_fresh_conflict(
        self,
    ) -> None:
        # The first write attempt may still apply, so what the retry then
        # observes cannot prove non-application.
        calendar = self.adapter()
        event = self.seed(calendar)
        assert event.event_ref is not None
        durable = self.launch(calendar)
        self.server.lose_write_before_commit = 1

        def human_edit() -> None:
            body = self.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)  # type: ignore[union-attr]
            assert body is not None
            self.server.human_edit(
                FAMILY_PATH, event.event_ref.resource_name, body.replace(b"dentist", b"HUMAN")  # type: ignore[union-attr]
            )

        self._after_first_write_attempt(human_edit, on_get=2)

        result = durable.update_calendar_event(self.update_request(event, "op-retry-conflict"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.provider.error_code, "version_conflict_after_possible_send")

    def test_absence_found_while_retrying_a_cancel_is_unproven(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.server.lose_write_before_commit = 1
        self._after_first_write_attempt(
            lambda: self.server._collections[FAMILY_PATH].resources.clear(),
            on_get=2,
        )

        result = durable.cancel_calendar_event(self.cancel_request(event, "op-retry-gone"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.AMBIGUOUS)
        self.assertEqual(result.provider.error_code, "event_absent_cause_unknown")

    def test_fresh_outcomes_stay_definite(self) -> None:
        # Positive controls: before any send, absence and a stale version are
        # proven non-effects and keep their definite reports.
        calendar = self.adapter()
        stale = self.seed(calendar)
        assert stale.event_ref is not None
        body = self.server.resource_body(FAMILY_PATH, stale.event_ref.resource_name)
        assert body is not None
        self.server.human_edit(FAMILY_PATH, stale.event_ref.resource_name, body.replace(b"dentist", b"HUMAN"))
        durable = self.launch(calendar)

        conflict = durable.cancel_calendar_event(self.cancel_request(stale, "op-fresh-stale"))
        self.server._collections[FAMILY_PATH].resources.clear()
        absent = durable.update_calendar_event(self.update_request(stale, "op-fresh-absent"))

        self.assertEqual(conflict.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(conflict.provider.error_code, "version_conflict")
        self.assertEqual(absent.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(absent.provider.error_code, "event_absent")
        self.assertEqual(self.server.conditional_writes, [])

    def test_operation_id_reuse_with_different_base_version_is_rejected(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        durable.update_calendar_event(self.update_request(event, "op-bind"))

        changed_base = dataclasses.replace(
            self.update_request(event, "op-bind"),
            proposal=dataclasses.replace(
                self.update_request(event, "op-bind").proposal,
                base_version=EventBaseVersion(
                    self.update_request(event, "x").proposal.base_version.version,
                    event.sequence + 5,
                ),
            ),
        )
        with self.assertRaises(OperationIdentityConflictError):
            durable.update_calendar_event(changed_base)
        with self.assertRaises(OperationIdentityConflictError):
            durable.cancel_calendar_event(self.cancel_request(event, "op-bind"))

    def test_provider_without_update_capability_fails_closed_without_a_request(
        self,
    ) -> None:
        profile = dataclasses.replace(IONOS_PROFILE, update_capability=ProviderCapability.NONE)
        calendar = self.adapter(profile)
        event = self.seed(calendar)
        durable = self.launch(calendar)
        self.requests.clear()

        result = durable.update_calendar_event(self.update_request(event, "op-none"))

        self.assertEqual(result.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(result.provider.error_code, "provider_not_recoverable")
        self.assertEqual(self.requests, [])

    def test_read_only_calendar_is_reported_as_not_performed(self) -> None:
        calendar = self.adapter()
        event = self.seed(calendar)
        durable = self.launch(calendar)
        assert event.event_ref is not None and event.version is not None
        request = DurableCalendarCancel(
            operation_id=OperationId("op-ro"),
            proposal=CancelCalendarEventProposal(
                event_ref=dataclasses.replace(event.event_ref, calendar_id="guardian-a"),
                base_version=EventBaseVersion(event.version, 0),
            ),
            authorization=EVIDENCE,
        )
        result = durable.cancel_calendar_event(request)
        self.assertEqual(result.provider.status, ProviderOutcomeStatus.FAILED)
        self.assertEqual(result.provider.error_code, "calendar_not_configured")


class ChangeServiceTests(_Base):
    """Guard-then-durable wiring for update/cancel through the service."""

    def seeded(self) -> tuple[InMemoryCalendarAdapter, CalendarEvent, CalendarActionService]:
        calendar = InMemoryCalendarAdapter()
        result = calendar.create_event(
            CreateCalendarEventProposal(
                title="Synthetic dentist", start=START, end=END, calendar_id="family"
            ),
            operation_id="seed",
        )
        assert result.event is not None
        durable = self.launch(calendar)
        guard = CedarGuard(POLICY, policy_version="test-policy-v1")
        return calendar, result.event, CalendarActionService(
            guard=guard, durable_actions=durable
        )

    def test_authorized_update_and_cancel_execute(self) -> None:
        calendar, event, service = self.seeded()
        assert event.event_ref is not None and event.version is not None
        base = EventBaseVersion(event.version, event.sequence)

        updated = service.update_event(
            UpdateCalendarEventProposal(
                event.event_ref, base, CalendarEventChanges(title="Moved")
            ),
            operation_id=OperationId("svc-upd"),
            authorization=authorization(),
        )
        self.assertTrue(updated.guard.allowed)
        assert updated.execution is not None
        self.assertEqual(updated.execution.business.status, BusinessOutcomeStatus.COMMITTED)
        self.assertEqual(
            render_calendar_change_response("update", updated),
            "I did update the calendar event.",
        )

        # The approved version is now stale: cancel must report a conflict.
        stale = service.cancel_event(
            CancelCalendarEventProposal(event.event_ref, base),
            operation_id=OperationId("svc-cancel-stale"),
            authorization=authorization(),
        )
        assert stale.execution is not None
        self.assertEqual(stale.execution.provider.error_code, "version_conflict")
        self.assertIn(
            "changed after it was approved", render_calendar_change_response("cancel", stale)
        )
        self.assertEqual(len(calendar.list_events(start=START, end=END)), 1)

    def test_unauthorized_or_model_provenance_changes_nothing(self) -> None:
        calendar, event, service = self.seeded()
        assert event.event_ref is not None and event.version is not None
        base = EventBaseVersion(event.version, event.sequence)

        denied = service.cancel_event(
            CancelCalendarEventProposal(event.event_ref, base),
            operation_id=OperationId("svc-denied"),
            authorization=authorization(InstructionProvenance.MODEL),
        )
        self.assertFalse(denied.guard.allowed)
        self.assertIsNone(denied.execution)
        self.assertEqual(len(calendar.list_events(start=START, end=END)), 1)
        self.assertIn(
            "not authorized", render_calendar_change_response("cancel", denied)
        )

    def test_guard_is_bound_to_the_proposals_calendar_not_caller_fields(self) -> None:
        _, event, service = self.seeded()
        assert event.event_ref is not None and event.version is not None
        other = dataclasses.replace(event.event_ref, calendar_id="guardian-a")

        response = service.cancel_event(
            CancelCalendarEventProposal(
                other, EventBaseVersion(event.version, event.sequence)
            ),
            operation_id=OperationId("svc-other"),
            authorization=dataclasses.replace(
                authorization(), resource="calendar:family", action="calendar.cancel"
            ),
        )
        self.assertFalse(response.guard.allowed)

    def test_invalid_proposal_is_rejected_before_authorization(self) -> None:
        _, event, service = self.seeded()
        assert event.event_ref is not None and event.version is not None
        with self.assertRaises(CalendarProposalValidationError):
            service.update_event(
                UpdateCalendarEventProposal(
                    event.event_ref,
                    EventBaseVersion(event.version, 0),
                    CalendarEventChanges(),
                ),
                operation_id=OperationId("svc-invalid"),
                authorization=authorization(),
            )


class RenderTests(unittest.TestCase):
    def _response(self, status, code):  # type: ignore[no-untyped-def]
        from ada.application.calendar_actions import CalendarActionResponse
        from ada.core.action_outcomes import (
            ActionExecutionResult,
            ProviderOutcome,
            business_outcome_from_provider,
        )
        from ada.core.authorization import GuardDecision, GuardEffect

        provider = ProviderOutcome(status=status, error_code=code)
        return CalendarActionResponse(
            guard=GuardDecision(GuardEffect.ALLOW, "matching_grant", (), "v"),
            execution=ActionExecutionResult(
                OperationId("op"), provider, business_outcome_from_provider(provider)
            ),
        )

    def test_messages_never_claim_more_than_the_outcome(self) -> None:
        absent = render_calendar_change_response(
            "cancel", self._response(ProviderOutcomeStatus.FAILED, "event_absent")
        )
        self.assertIn("no longer exists", absent)
        self.assertNotIn("did cancel", absent)

        ambiguous = render_calendar_change_response(
            "update", self._response(ProviderOutcomeStatus.AMBIGUOUS, "x")
        )
        self.assertIn("cannot confirm", ambiguous)

        unproven_absence = render_calendar_change_response(
            "cancel",
            self._response(ProviderOutcomeStatus.AMBIGUOUS, "event_absent_cause_unknown"),
        )
        self.assertIn("no longer exists", unproven_absence)
        self.assertIn("cannot confirm whether my cancel caused", unproven_absence)
        self.assertNotIn("no change", unproven_absence)

        after_send = render_calendar_change_response(
            "update",
            self._response(
                ProviderOutcomeStatus.AMBIGUOUS, "version_conflict_after_possible_send"
            ),
        )
        self.assertIn("earlier attempt may already have reached", after_send)
        self.assertNotIn("Nothing was overwritten", after_send)
        self.assertNotIn("no change", after_send)

        scope = render_calendar_change_response(
            "update",
            self._response(ProviderOutcomeStatus.FAILED, "recurring_event_read_only"),
        )
        self.assertIn("read-only", scope)


if __name__ == "__main__":
    unittest.main()
