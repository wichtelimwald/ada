from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import CalendarCreateStatus, CalendarPort


class CalendarPortContractTests:
    """Shared behavioral contract every ``CalendarPort`` adapter must satisfy.

    Mix this into a concrete ``unittest.TestCase`` that implements
    ``make_calendar()``. It deliberately does not inherit ``TestCase`` itself
    so test discovery never collects it standalone (ADR-0009 section 2: every
    adapter and profile must pass this shared suite).
    """

    def make_calendar(self) -> CalendarPort:
        raise NotImplementedError

    def make_proposal(self, **overrides: object) -> CreateCalendarEventProposal:
        defaults: dict[str, object] = {
            "title": "Contract test event",
            "start": datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
            "end": datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc),
            "calendar_id": "family",
            "location": None,
        }
        defaults.update(overrides)
        return CreateCalendarEventProposal(**defaults)  # type: ignore[arg-type]

    def test_declares_a_create_capability(self) -> None:
        calendar = self.make_calendar()
        self.assertIsInstance(calendar.create_capability, ProviderCapability)  # type: ignore[attr-defined]

    def test_create_then_list_returns_the_event_in_range(self) -> None:
        calendar = self.make_calendar()
        proposal = self.make_proposal()

        result = calendar.create_event(proposal, operation_id="contract-create-list")

        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)  # type: ignore[attr-defined]
        assert result.event is not None

        events = calendar.list_events(
            start=proposal.start - timedelta(hours=1),
            end=proposal.end + timedelta(hours=1),
        )
        self.assertIn(  # type: ignore[attr-defined]
            result.event.event_id,
            {event.event_id for event in events},
        )

    def test_list_events_excludes_events_outside_the_window(self) -> None:
        calendar = self.make_calendar()
        proposal = self.make_proposal(title="Outside window")

        result = calendar.create_event(
            proposal, operation_id="contract-outside-window"
        )
        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)  # type: ignore[attr-defined]
        assert result.event is not None

        events = calendar.list_events(
            start=proposal.start + timedelta(days=10),
            end=proposal.end + timedelta(days=10, hours=1),
        )
        self.assertNotIn(  # type: ignore[attr-defined]
            result.event.event_id,
            {event.event_id for event in events},
        )

    def test_repeating_create_with_same_operation_id_does_not_duplicate(
        self,
    ) -> None:
        calendar = self.make_calendar()
        proposal = self.make_proposal()
        operation_id = "contract-idempotent-replay"

        first = calendar.create_event(proposal, operation_id=operation_id)
        second = calendar.create_event(proposal, operation_id=operation_id)

        self.assertEqual(first.status, CalendarCreateStatus.COMMITTED)  # type: ignore[attr-defined]
        self.assertEqual(second.status, CalendarCreateStatus.COMMITTED)  # type: ignore[attr-defined]
        assert first.event is not None and second.event is not None
        self.assertEqual(first.event.event_id, second.event.event_id)  # type: ignore[attr-defined]

        events = calendar.list_events(
            start=proposal.start - timedelta(hours=1),
            end=proposal.end + timedelta(hours=1),
        )
        matching = [
            event for event in events if event.event_id == first.event.event_id
        ]
        self.assertEqual(len(matching), 1)  # type: ignore[attr-defined]

    def test_reconcile_create_proves_an_existing_commit(self) -> None:
        calendar = self.make_calendar()
        proposal = self.make_proposal()
        operation_id = "contract-reconcile"

        created = calendar.create_event(proposal, operation_id=operation_id)
        self.assertEqual(created.status, CalendarCreateStatus.COMMITTED)  # type: ignore[attr-defined]
        assert created.event is not None

        reconciled = calendar.reconcile_create(operation_id=operation_id)

        if calendar.create_capability is ProviderCapability.NONE:
            self.assertIsNone(reconciled)  # type: ignore[attr-defined]
        else:
            assert reconciled is not None
            self.assertEqual(reconciled.event_id, created.event.event_id)  # type: ignore[attr-defined]

    def test_reconcile_create_returns_none_for_unknown_operation(self) -> None:
        calendar = self.make_calendar()

        self.assertIsNone(  # type: ignore[attr-defined]
            calendar.reconcile_create(operation_id="contract-never-created")
        )
