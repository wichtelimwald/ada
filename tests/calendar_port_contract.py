from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import (
    CalendarEventChanges,
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    EventBaseVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import (
    CalendarChangeStatus,
    CalendarCreateStatus,
    CalendarEvent,
    CalendarPort,
)


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

    # -- update / cancel -----------------------------------------------------

    def _created_event(self, calendar: CalendarPort, operation_id: str) -> CalendarEvent:
        result = calendar.create_event(self.make_proposal(), operation_id=operation_id)
        assert result.event is not None and result.event.version is not None
        return result.event

    @staticmethod
    def _update(event: CalendarEvent, **changes: object) -> UpdateCalendarEventProposal:
        assert event.event_ref is not None and event.version is not None
        return UpdateCalendarEventProposal(
            event_ref=event.event_ref,
            base_version=EventBaseVersion(event.version, event.sequence),
            changes=CalendarEventChanges(**changes),  # type: ignore[arg-type]
        )

    @staticmethod
    def _cancel(event: CalendarEvent) -> CancelCalendarEventProposal:
        assert event.event_ref is not None and event.version is not None
        return CancelCalendarEventProposal(
            event_ref=event.event_ref,
            base_version=EventBaseVersion(event.version, event.sequence),
        )

    def _titles(self, calendar: CalendarPort) -> set[str]:
        proposal = self.make_proposal()
        return {
            event.title
            for event in calendar.list_events(
                start=proposal.start - timedelta(hours=1),
                end=proposal.end + timedelta(hours=1),
            )
        }

    def test_declares_update_and_cancel_capabilities(self) -> None:
        calendar = self.make_calendar()
        self.assertIsInstance(calendar.update_capability, ProviderCapability)  # type: ignore[attr-defined]
        self.assertIsInstance(calendar.cancel_capability, ProviderCapability)  # type: ignore[attr-defined]

    def test_update_with_the_approved_version_changes_the_event(self) -> None:
        calendar = self.make_calendar()
        event = self._created_event(calendar, "contract-update")

        result = calendar.update_event(
            self._update(event, title="Renamed"), operation_id="contract-update-1"
        )

        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)  # type: ignore[attr-defined]
        self.assertIn("Renamed", self._titles(calendar))  # type: ignore[attr-defined]
        self.assertNotIn("Contract test event", self._titles(calendar))  # type: ignore[attr-defined]

    def test_update_with_a_stale_version_is_a_conflict_and_changes_nothing(
        self,
    ) -> None:
        calendar = self.make_calendar()
        event = self._created_event(calendar, "contract-stale")
        first = calendar.update_event(
            self._update(event, title="First"), operation_id="contract-stale-1"
        )
        self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)  # type: ignore[attr-defined]

        stale = calendar.update_event(
            self._update(event, title="Second"), operation_id="contract-stale-2"
        )

        self.assertEqual(stale.status, CalendarChangeStatus.CONFLICT)  # type: ignore[attr-defined]
        self.assertIn("First", self._titles(calendar))  # type: ignore[attr-defined]
        self.assertNotIn("Second", self._titles(calendar))  # type: ignore[attr-defined]

    def test_replaying_an_update_does_not_apply_it_twice(self) -> None:
        calendar = self.make_calendar()
        event = self._created_event(calendar, "contract-update-replay")
        proposal = self._update(event, title="Once")

        first = calendar.update_event(proposal, operation_id="contract-replay-op")
        second = calendar.update_event(proposal, operation_id="contract-replay-op")

        self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)  # type: ignore[attr-defined]
        self.assertEqual(second.status, CalendarChangeStatus.COMMITTED)  # type: ignore[attr-defined]
        assert first.event is not None and second.event is not None
        self.assertEqual(first.event.sequence, second.event.sequence)  # type: ignore[attr-defined]

    def test_cancel_removes_the_event_and_a_repeat_reports_absent(self) -> None:
        calendar = self.make_calendar()
        event = self._created_event(calendar, "contract-cancel")
        proposal = self._cancel(event)

        first = calendar.cancel_event(proposal, operation_id="contract-cancel-1")
        second = calendar.cancel_event(proposal, operation_id="contract-cancel-1")

        self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)  # type: ignore[attr-defined]
        self.assertEqual(second.status, CalendarChangeStatus.ABSENT)  # type: ignore[attr-defined]
        self.assertNotIn("Contract test event", self._titles(calendar))  # type: ignore[attr-defined]

    def test_cancel_with_a_stale_version_is_a_conflict_and_keeps_the_event(
        self,
    ) -> None:
        calendar = self.make_calendar()
        event = self._created_event(calendar, "contract-cancel-stale")
        calendar.update_event(
            self._update(event, title="Changed"), operation_id="contract-cs-1"
        )

        result = calendar.cancel_event(
            self._cancel(event), operation_id="contract-cs-2"
        )

        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)  # type: ignore[attr-defined]
        self.assertIn("Changed", self._titles(calendar))  # type: ignore[attr-defined]
