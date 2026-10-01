from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import httpx2
import icalendar

from ada.adapters.caldav import mapping
from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.core.actions import (
    CalendarEventChanges,
    CancelCalendarEventProposal,
    EventBaseVersion,
    EventVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import (
    CalendarChangeResult,
    CalendarChangeStatus,
    CalendarEvent,
    CalendarCreateStatus,
    EventRef,
)
from caldav_fake_ionos_server import FakeIonosCalDAVServer
from caldav_test_support import (
    BASE_URL,
    FAKE_AUTH,
    FAMILY_PATH,
    build_fake_server,
    default_family_ref,
    default_read_only_ref,
)

START = datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc)
END = datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc)

SYNTHETIC_TITLE = "Synthetic dentist"


def _ical(*vevent_lines: str) -> bytes:
    body = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Test//EN",
            "BEGIN:VEVENT",
            "UID:seeded-uid-1@example.test",
            "DTSTAMP:20260901T000000Z",
            "SUMMARY:Seeded",
            *vevent_lines,
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    return body.encode("utf-8")


class _Fixture:
    def __init__(self) -> None:
        self.server: FakeIonosCalDAVServer = build_fake_server()
        self.requests: list[tuple[str, str]] = []

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            self.requests.append((request.method, request.url.path))
            return self.server(request)

        self.adapter = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(default_family_ref(), default_read_only_ref()),
            profile=IONOS_PROFILE,
            transport=httpx2.MockTransport(dispatch),
            clock=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        )

    def methods(self) -> list[str]:
        return [method for method, _ in self.requests]

    def create(self, operation_id: str = "seed-1", **overrides: object) -> CalendarEvent:
        from ada.core.actions import CreateCalendarEventProposal

        fields: dict[str, object] = {
            "title": SYNTHETIC_TITLE,
            "start": START,
            "end": END,
            "calendar_id": "family",
            "location": "Clinic",
        }
        fields.update(overrides)
        result = self.adapter.create_event(
            CreateCalendarEventProposal(**fields),  # type: ignore[arg-type]
            operation_id=operation_id,
        )
        assert result.status is CalendarCreateStatus.COMMITTED and result.event
        return result.event

    def human_edit(self, event: CalendarEvent, title: str = "Edited by a human") -> str:
        assert event.event_ref is not None
        name = event.event_ref.resource_name
        body = self.server.resource_body(FAMILY_PATH, name)
        assert body is not None
        calendar = icalendar.Calendar.from_ical(body)
        vevent = next(iter(calendar.walk("VEVENT")))
        vevent["summary"] = title
        if mapping.OPERATION_MARKER_PROPERTY in vevent:
            del vevent[mapping.OPERATION_MARKER_PROPERTY]
        return self.server.human_edit(FAMILY_PATH, name, calendar.to_ical())

    def stored(self, event: CalendarEvent) -> icalendar.cal.Component:
        assert event.event_ref is not None
        body = self.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)
        assert body is not None
        return next(iter(icalendar.Calendar.from_ical(body).walk("VEVENT")))


def base_of(event: CalendarEvent) -> EventBaseVersion:
    assert event.version is not None
    return EventBaseVersion(version=event.version, sequence=event.sequence)


def update_of(event: CalendarEvent, **changes: object) -> UpdateCalendarEventProposal:
    assert event.event_ref is not None
    return UpdateCalendarEventProposal(
        event_ref=event.event_ref,
        base_version=base_of(event),
        changes=CalendarEventChanges(**changes),  # type: ignore[arg-type]
    )


def cancel_of(event: CalendarEvent) -> CancelCalendarEventProposal:
    assert event.event_ref is not None
    return CancelCalendarEventProposal(
        event_ref=event.event_ref, base_version=base_of(event)
    )


class CalDAVUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()
        self.addCleanup(self.fx.adapter.close)

    def test_update_writes_if_match_base_version_sequence_plus_one_and_marker(
        self,
    ) -> None:
        event = self.fx.create()
        base_etag = f'"{self.fx.server.resource_etag(FAMILY_PATH, event.event_ref.resource_name)}"'  # type: ignore[union-attr]
        before = self.fx.stored(event)
        before_dtstamp = before.get("dtstamp").dt

        result = self.fx.adapter.update_event(
            update_of(event, title="Synthetic dentist (moved)"),
            operation_id="upd-1",
        )

        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(self.fx.server.conditional_writes, [("PUT", base_etag)])
        stored = self.fx.stored(event)
        self.assertEqual(str(stored.get("summary")), "Synthetic dentist (moved)")
        self.assertEqual(int(stored.get("sequence")), event.sequence + 1)
        self.assertEqual(
            mapping.component_operation_marker(stored),
            mapping.derive_operation_marker("upd-1"),
        )
        self.assertGreaterEqual(stored.get("dtstamp").dt, before_dtstamp)
        # Verified read-back carries the new version and sequence.
        assert result.event is not None and result.event.version is not None
        self.assertNotEqual(result.event.version, event.version)
        self.assertEqual(result.event.sequence, event.sequence + 1)
        self.assertEqual(result.event.title, "Synthetic dentist (moved)")

    def test_update_preserves_unchanged_properties(self) -> None:
        self.fx.server.seed_resource(
            FAMILY_PATH,
            "seeded.ics",
            _ical(
                "DTSTART:20261012T160000Z",
                "DTEND:20261012T163000Z",
                "LOCATION:Clinic",
                "DESCRIPTION:Bring the insurance card",
                "SEQUENCE:3",
            ),
        )
        listed = self.fx.adapter.list_events(start=START - timedelta(hours=1), end=END)
        event = next(e for e in listed if e.event_id == "seeded.ics")
        self.assertEqual(event.sequence, 3)

        result = self.fx.adapter.update_event(
            update_of(event, location="Clinic North"), operation_id="upd-keep"
        )

        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        body = self.fx.server.resource_body(FAMILY_PATH, "seeded.ics")
        assert body is not None
        stored = next(iter(icalendar.Calendar.from_ical(body).walk("VEVENT")))
        self.assertEqual(str(stored.get("description")), "Bring the insurance card")
        self.assertEqual(str(stored.get("location")), "Clinic North")
        self.assertEqual(str(stored.get("summary")), "Seeded")
        self.assertEqual(int(stored.get("sequence")), 4)

    def test_start_only_change_keeps_duration_and_end_only_keeps_start(self) -> None:
        event = self.fx.create()
        moved = START + timedelta(hours=2)
        first = self.fx.adapter.update_event(
            update_of(event, start=moved), operation_id="upd-start"
        )
        assert first.event is not None
        self.assertEqual(first.event.start, moved)
        self.assertEqual(first.event.end, moved + (END - START))

        later_end = moved + timedelta(hours=3)
        second = self.fx.adapter.update_event(
            update_of(first.event, end=later_end), operation_id="upd-end"
        )
        assert second.event is not None
        self.assertEqual(second.event.start, moved)
        self.assertEqual(second.event.end, later_end)

    def test_end_not_after_start_is_rejected_without_writing(self) -> None:
        event = self.fx.create()
        result = self.fx.adapter.update_event(
            update_of(event, end=START - timedelta(minutes=5)),
            operation_id="upd-bad-range",
        )
        self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
        self.assertEqual(result.error_code, "invalid_time_range")
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_human_edit_after_approval_is_a_conflict_and_nothing_is_written(
        self,
    ) -> None:
        event = self.fx.create()
        self.fx.human_edit(event)

        result = self.fx.adapter.update_event(
            update_of(event, title="Ada's change"), operation_id="upd-conflict"
        )

        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)
        self.assertEqual(self.fx.server.conditional_writes, [])
        self.assertEqual(str(self.fx.stored(event).get("summary")), "Edited by a human")

    def test_human_edit_between_read_and_write_is_a_412_conflict(self) -> None:
        event = self.fx.create()
        self.fx.server.before_next_conditional_write = lambda: self.fx.human_edit(event)

        result = self.fx.adapter.update_event(
            update_of(event, title="Ada's change"), operation_id="upd-race"
        )

        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)
        # The human edit survived, and Ada only ever sent the approved tag.
        self.assertEqual(str(self.fx.stored(event).get("summary")), "Edited by a human")
        approved = f'"{event.version.strip(chr(34))}"'  # type: ignore[union-attr]
        self.assertEqual(self.fx.server.conditional_writes, [("PUT", approved)])

    def test_base_sequence_mismatch_is_a_conflict(self) -> None:
        event = self.fx.create()
        proposal = UpdateCalendarEventProposal(
            event_ref=event.event_ref,  # type: ignore[arg-type]
            base_version=EventBaseVersion(version=event.version, sequence=7),  # type: ignore[arg-type]
            changes=CalendarEventChanges(title="x"),
        )
        result = self.fx.adapter.update_event(proposal, operation_id="upd-seq")
        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_unquoted_base_version_is_sent_quoted(self) -> None:
        event = self.fx.create()
        assert event.version is not None
        unquoted = event.version.strip('"')
        proposal = UpdateCalendarEventProposal(
            event_ref=event.event_ref,  # type: ignore[arg-type]
            base_version=EventBaseVersion(
                version=EventVersion(unquoted), sequence=event.sequence
            ),
            changes=CalendarEventChanges(title="x"),
        )
        result = self.fx.adapter.update_event(proposal, operation_id="upd-quote")
        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(
            self.fx.server.conditional_writes, [("PUT", f'"{unquoted}"')]
        )

    def test_replay_after_commit_is_committed_by_marker_without_a_second_write(
        self,
    ) -> None:
        event = self.fx.create()
        proposal = update_of(event, title="Once")

        first = self.fx.adapter.update_event(proposal, operation_id="upd-replay")
        second = self.fx.adapter.update_event(proposal, operation_id="upd-replay")

        self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(second.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(len(self.fx.server.conditional_writes), 1)
        self.assertEqual(int(self.fx.stored(event).get("sequence")), event.sequence + 1)

    def test_lost_response_after_commit_reconciles_to_committed_by_marker(
        self,
    ) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_response_after_commit = 1

        result = self.fx.adapter.update_event(
            update_of(event, title="Applied"), operation_id="upd-lost-response"
        )

        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(len(self.fx.server.conditional_writes), 1)
        self.assertEqual(str(self.fx.stored(event).get("summary")), "Applied")

    def test_lost_request_before_commit_is_not_applied_and_replay_applies_once(
        self,
    ) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_before_commit = 1
        proposal = update_of(event, title="Applied later")

        first = self.fx.adapter.update_event(proposal, operation_id="upd-lost-request")
        self.assertEqual(first.status, CalendarChangeStatus.NOT_APPLIED)
        self.assertEqual(str(self.fx.stored(event).get("summary")), SYNTHETIC_TITLE)

        second = self.fx.adapter.update_event(proposal, operation_id="upd-lost-request")
        self.assertEqual(second.status, CalendarChangeStatus.COMMITTED)
        # Both attempts carried the same, approved precondition.
        tags = {tag for _, tag in self.fx.server.conditional_writes}
        self.assertEqual(len(tags), 1)
        self.assertEqual(int(self.fx.stored(event).get("sequence")), event.sequence + 1)

    def test_lost_response_then_human_edit_stays_ambiguous(self) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_response_after_commit = 1
        # A human edit lands right after Ada's write but before Ada re-reads:
        # it also strips Ada's marker, so the write cannot be proven.
        real_get = self.fx.server._get

        edited = {"done": False}

        def get_then_edit(path: str) -> httpx2.Response:
            if not edited["done"] and self.fx.server.conditional_writes:
                edited["done"] = True
                self.fx.human_edit(event)
            return real_get(path)

        self.fx.server._get = get_then_edit  # type: ignore[method-assign]

        result = self.fx.adapter.update_event(
            update_of(event, title="Ada"), operation_id="upd-ambiguous"
        )

        self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "changed_after_ambiguous_send")
        self.assertEqual(len(self.fx.server.conditional_writes), 1)

    def test_unexpected_status_with_unchanged_base_is_not_applied(self) -> None:
        event = self.fx.create()
        self.fx.server.conditional_write_status = 503

        result = self.fx.adapter.update_event(
            update_of(event, title="x"), operation_id="upd-503"
        )

        self.assertEqual(result.status, CalendarChangeStatus.NOT_APPLIED)

    def test_reconciliation_read_failure_is_ambiguous(self) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_response_after_commit = 1
        real_get = self.fx.server._get

        def failing_get(path: str) -> httpx2.Response:
            if self.fx.server.conditional_writes:
                raise httpx2.ReadTimeout("reconciliation read failed")
            return real_get(path)

        self.fx.server._get = failing_get  # type: ignore[method-assign]

        result = self.fx.adapter.update_event(
            update_of(event, title="x"), operation_id="upd-recon-fail"
        )
        self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "reconciliation_failed")

    def _delete_after_write(self, event: CalendarEvent) -> None:
        """Someone else deletes the event after Ada's write was sent but
        before Ada re-reads it for reconciliation."""

        assert event.event_ref is not None
        real_get = self.fx.server._get
        state = {"done": False}

        def get_after_delete(path: str) -> httpx2.Response:
            if not state["done"] and self.fx.server.conditional_writes:
                state["done"] = True
                self.fx.server._collections[FAMILY_PATH].resources.clear()
            return real_get(path)

        self.fx.server._get = get_after_delete  # type: ignore[method-assign]

    def test_update_absent_after_ambiguous_send_is_ambiguous_not_a_non_commit(
        self,
    ) -> None:
        # Absence does not prove the update did not commit: it may have
        # committed and the event been deleted afterwards. Both histories
        # must stay indistinguishable, hence ambiguous.
        for label, fault in (
            ("lost response after commit", "lose_write_response_after_commit"),
            ("lost request before commit", "lose_write_before_commit"),
        ):
            with self.subTest(label):
                self.tearDown()
                self.setUp()
                event = self.fx.create()
                setattr(self.fx.server, fault, 1)
                self._delete_after_write(event)

                result = self.fx.adapter.update_event(
                    update_of(event, title="x"), operation_id="upd-gone"
                )

                self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)
                self.assertEqual(result.error_code, "event_absent_cause_unknown")
                self.assertEqual(len(self.fx.server.conditional_writes), 1)

    def test_update_of_an_absent_event_reports_absent_without_writing(self) -> None:
        event = self.fx.create()
        assert event.event_ref is not None
        collection = self.fx.server._collections[FAMILY_PATH]
        collection.resources.clear()

        result = self.fx.adapter.update_event(
            update_of(event, title="x"), operation_id="upd-absent"
        )
        self.assertEqual(result.status, CalendarChangeStatus.ABSENT)
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_pre_read_transport_failure_is_rejected_before_any_write(self) -> None:
        event = self.fx.create()
        real_get = self.fx.server._get

        def failing_get(path: str) -> httpx2.Response:
            raise httpx2.ConnectError("provider unreachable")

        self.fx.server._get = failing_get  # type: ignore[method-assign]
        result = self.fx.adapter.update_event(
            update_of(event, title="x"), operation_id="upd-pre-read"
        )
        self.fx.server._get = real_get  # type: ignore[method-assign]

        self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
        self.assertEqual(result.error_code, "pre_read_failed")
        self.assertEqual(self.fx.server.conditional_writes, [])


class CalDAVMarkerBeforeWriteScopeTests(unittest.TestCase):
    """A preserved operation marker proves Ada's earlier update committed even
    if the event was later changed into a shape Ada may no longer write.

    Write-scope refusals only forbid a *new* write; they must not erase
    reconciliation evidence (ADR-0009 section 6).
    """

    SHAPES = {
        "attendee": "ATTENDEE:mailto:someone@example.test",
        "recurrence": "RRULE:FREQ=WEEKLY;COUNT=4",
        "series-with-override": None,  # a second VEVENT, see _reshape
    }

    def setUp(self) -> None:
        self.fx = _Fixture()
        self.addCleanup(self.fx.adapter.close)

    def _reshape(self, event: CalendarEvent, shape: str) -> None:
        """A provider/user edit that keeps Ada's marker but changes the shape."""

        assert event.event_ref is not None
        body = self.fx.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)
        assert body is not None
        calendar = icalendar.Calendar.from_ical(body)
        vevent = next(iter(calendar.walk("VEVENT")))
        if shape == "attendee":
            vevent.add("attendee", "mailto:someone@example.test")
        elif shape == "recurrence":
            vevent.add("rrule", {"FREQ": "WEEKLY", "COUNT": 4})
        else:
            override = icalendar.Event()
            override.add("uid", str(vevent.get("uid")))
            override.add("dtstamp", datetime(2026, 9, 1, tzinfo=timezone.utc))
            override.add("dtstart", START + timedelta(days=7))
            override.add("dtend", END + timedelta(days=7))
            override.add("recurrence-id", START + timedelta(days=7))
            calendar.add_component(override)
            vevent.add("rrule", {"FREQ": "WEEKLY", "COUNT": 4})
        self.fx.server.human_edit(
            FAMILY_PATH, event.event_ref.resource_name, calendar.to_ical()
        )

    def test_replay_after_commit_is_committed_even_if_the_event_left_the_write_scope(
        self,
    ) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape):
                self.tearDown()
                self.setUp()
                event = self.fx.create()
                proposal = update_of(event, title="Applied once")
                first = self.fx.adapter.update_event(proposal, operation_id="upd-scope")
                self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)
                self._reshape(event, shape)

                replay = self.fx.adapter.update_event(proposal, operation_id="upd-scope")

                self.assertEqual(replay.status, CalendarChangeStatus.COMMITTED)
                self.assertEqual(len(self.fx.server.conditional_writes), 1)

    def test_reconciliation_after_a_lost_response_survives_a_shape_change(self) -> None:
        for shape in self.SHAPES:
            with self.subTest(shape):
                self.tearDown()
                self.setUp()
                event = self.fx.create()
                self.fx.server.lose_write_response_after_commit = 1
                real_get = self.fx.server._get
                state = {"done": False}

                def get_after_reshape(path: str, _real=real_get, _state=state, _event=event, _shape=shape) -> httpx2.Response:  # noqa: E501
                    if not _state["done"] and self.fx.server.conditional_writes:
                        _state["done"] = True
                        self._reshape(_event, _shape)
                    return _real(path)

                self.fx.server._get = get_after_reshape  # type: ignore[method-assign]

                result = self.fx.adapter.update_event(
                    update_of(event, title="Applied"), operation_id="upd-recon-scope"
                )

                self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
                self.assertEqual(len(self.fx.server.conditional_writes), 1)

    def test_without_a_marker_the_scope_refusal_still_applies(self) -> None:
        event = self.fx.create()
        assert event.event_ref is not None
        body = self.fx.server.resource_body(FAMILY_PATH, event.event_ref.resource_name)
        assert body is not None
        self.fx.server.human_edit(
            FAMILY_PATH,
            event.event_ref.resource_name,
            body.replace(b"END:VEVENT", b"ATTENDEE:mailto:someone@example.test\r\nEND:VEVENT"),
        )
        current = self.fx.adapter.list_events(
            start=START - timedelta(hours=1), end=END + timedelta(hours=1)
        )[0]

        result = self.fx.adapter.update_event(
            update_of(current, title="x"), operation_id="upd-no-marker"
        )

        self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
        self.assertEqual(result.error_code, "attendee_event_read_only")
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_unparsable_provider_data_is_a_typed_pre_read_failure(self) -> None:
        event = self.fx.create()
        assert event.event_ref is not None
        self.fx.server.human_edit(
            FAMILY_PATH, event.event_ref.resource_name, b"this is not iCalendar"
        )

        result = self.fx.adapter.update_event(
            update_of(event, title="x"), operation_id="upd-garbage"
        )

        self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
        self.assertEqual(result.error_code, "pre_read_failed")


class CalDAVCancelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()
        self.addCleanup(self.fx.adapter.close)

    def test_cancel_deletes_exactly_the_intended_event_with_if_match(self) -> None:
        keep = self.fx.create("seed-keep", title="Keep me")
        gone = self.fx.create("seed-gone", title="Cancel me")
        assert gone.event_ref is not None and gone.version is not None

        result = self.fx.adapter.cancel_event(cancel_of(gone), operation_id="cancel-1")

        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(
            self.fx.server.conditional_writes, [("DELETE", str(gone.version))]
        )
        self.assertIsNone(
            self.fx.server.resource_body(FAMILY_PATH, gone.event_ref.resource_name)
        )
        assert keep.event_ref is not None
        self.assertIsNotNone(
            self.fx.server.resource_body(FAMILY_PATH, keep.event_ref.resource_name)
        )

    def test_repeated_cancel_reports_absent_and_sends_no_second_delete(self) -> None:
        event = self.fx.create()
        proposal = cancel_of(event)
        first = self.fx.adapter.cancel_event(proposal, operation_id="cancel-1")
        second = self.fx.adapter.cancel_event(proposal, operation_id="cancel-1")

        self.assertEqual(first.status, CalendarChangeStatus.COMMITTED)
        self.assertEqual(second.status, CalendarChangeStatus.ABSENT)
        self.assertEqual(self.fx.methods().count("DELETE"), 1)

    def test_human_edit_after_approval_is_a_conflict_and_event_survives(self) -> None:
        event = self.fx.create()
        self.fx.human_edit(event)

        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-c")

        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)
        self.assertNotIn("DELETE", self.fx.methods())
        self.assertEqual(str(self.fx.stored(event).get("summary")), "Edited by a human")

    def test_human_edit_between_read_and_delete_is_a_412_conflict(self) -> None:
        event = self.fx.create()
        self.fx.server.before_next_conditional_write = lambda: self.fx.human_edit(event)

        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-r")

        self.assertEqual(result.status, CalendarChangeStatus.CONFLICT)
        self.assertEqual(str(self.fx.stored(event).get("summary")), "Edited by a human")

    def test_lost_response_after_delete_knows_absence_but_not_its_cause(self) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_response_after_commit = 1

        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-l")

        # The goal state (absent) is known, but Ada cannot prove its own
        # DELETE caused it: not ABSENT (which means "nothing applied").
        self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "event_absent_cause_unknown")

    def test_lost_request_then_deletion_by_someone_else_is_the_same_unproven_state(
        self,
    ) -> None:
        event = self.fx.create()
        assert event.event_ref is not None
        self.fx.server.lose_write_before_commit = 1
        real_get = self.fx.server._get
        state = {"done": False}

        def get_after_delete(path: str) -> httpx2.Response:
            if not state["done"] and self.fx.server.conditional_writes:
                state["done"] = True
                self.fx.server._collections[FAMILY_PATH].resources.clear()
            return real_get(path)

        self.fx.server._get = get_after_delete  # type: ignore[method-assign]

        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-x")

        self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "event_absent_cause_unknown")

    def test_absence_before_any_send_is_a_proven_non_effect(self) -> None:
        event = self.fx.create()
        self.fx.server._collections[FAMILY_PATH].resources.clear()

        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-p")

        self.assertEqual(result.status, CalendarChangeStatus.ABSENT)
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_lost_request_before_delete_is_not_applied_and_replay_deletes_once(
        self,
    ) -> None:
        event = self.fx.create()
        self.fx.server.lose_write_before_commit = 1
        proposal = cancel_of(event)

        first = self.fx.adapter.cancel_event(proposal, operation_id="cancel-nl")
        second = self.fx.adapter.cancel_event(proposal, operation_id="cancel-nl")

        self.assertEqual(first.status, CalendarChangeStatus.NOT_APPLIED)
        self.assertEqual(second.status, CalendarChangeStatus.COMMITTED)
        tags = {tag for _, tag in self.fx.server.conditional_writes}
        self.assertEqual(tags, {str(event.version)})

    def test_edit_after_lost_delete_response_stays_ambiguous(self) -> None:
        event = self.fx.create()
        assert event.event_ref is not None
        # The DELETE is answered 503 without being applied and a human edit
        # then changes the event before Ada re-reads it.
        self.fx.server.conditional_write_status = 503
        real_get = self.fx.server._get
        edited = {"done": False}

        def get_then_edit(path: str) -> httpx2.Response:
            if not edited["done"] and self.fx.server.conditional_writes:
                edited["done"] = True
                self.fx.human_edit(event)
            return real_get(path)

        self.fx.server._get = get_then_edit  # type: ignore[method-assign]
        result = self.fx.adapter.cancel_event(cancel_of(event), operation_id="cancel-a")
        self.assertEqual(result.status, CalendarChangeStatus.AMBIGUOUS)


class CalDAVWriteScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()
        self.addCleanup(self.fx.adapter.close)

    def _seeded(self, name: str, *lines: str, path: str = FAMILY_PATH) -> CalendarEvent:
        self.fx.server.seed_resource(path, name, _ical(*lines))
        events = self.fx.adapter.list_events(
            start=START - timedelta(days=1), end=END + timedelta(days=1)
        )
        return next(e for e in events if e.event_id.startswith(name))

    def _assert_refused(
        self, result: CalendarChangeResult, code: str
    ) -> None:
        self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
        self.assertEqual(result.error_code, code)
        self.assertEqual(self.fx.server.conditional_writes, [])

    def test_recurring_series_is_refused_for_update_and_cancel(self) -> None:
        event = self._seeded(
            "series.ics",
            "DTSTART:20261012T160000Z",
            "DTEND:20261012T163000Z",
            "RRULE:FREQ=WEEKLY;COUNT=4",
        )
        self._assert_refused(
            self.fx.adapter.update_event(update_of(event, title="x"), operation_id="u"),
            "recurring_event_read_only",
        )
        self._assert_refused(
            self.fx.adapter.cancel_event(cancel_of(event), operation_id="c"),
            "recurring_event_read_only",
        )

    def test_single_occurrence_override_is_refused(self) -> None:
        # A lone override is not listed by the read path, so address it by
        # its resource name and the server's current entity tag.
        self.fx.server.seed_resource(
            FAMILY_PATH,
            "override.ics",
            _ical(
                "DTSTART:20261012T160000Z",
                "DTEND:20261012T163000Z",
                "RECURRENCE-ID:20261012T160000Z",
            ),
        )
        etag = self.fx.server.resource_etag(FAMILY_PATH, "override.ics")
        assert etag is not None
        proposal = UpdateCalendarEventProposal(
            event_ref=EventRef(calendar_id="family", resource_name="override.ics"),
            base_version=EventBaseVersion(version=EventVersion(f'"{etag}"'), sequence=0),
            changes=CalendarEventChanges(title="x"),
        )
        self._assert_refused(
            self.fx.adapter.update_event(proposal, operation_id="u"),
            "recurring_event_read_only",
        )

    def test_event_with_attendees_is_refused(self) -> None:
        event = self._seeded(
            "attendees.ics",
            "DTSTART:20261012T160000Z",
            "DTEND:20261012T163000Z",
            "ATTENDEE:mailto:someone@example.test",
        )
        self._assert_refused(
            self.fx.adapter.update_event(update_of(event, title="x"), operation_id="u"),
            "attendee_event_read_only",
        )
        self._assert_refused(
            self.fx.adapter.cancel_event(cancel_of(event), operation_id="c"),
            "attendee_event_read_only",
        )

    def test_all_day_time_change_is_refused_but_title_change_is_allowed(self) -> None:
        event = self._seeded(
            "allday.ics",
            "DTSTART;VALUE=DATE:20261012",
            "DTEND;VALUE=DATE:20261013",
        )
        self._assert_refused(
            self.fx.adapter.update_event(
                update_of(event, start=START), operation_id="u-time"
            ),
            "all_day_time_change_unsupported",
        )
        result = self.fx.adapter.update_event(
            update_of(event, title="Renamed"), operation_id="u-title"
        )
        self.assertEqual(result.status, CalendarChangeStatus.COMMITTED)
        assert result.event is not None
        self.assertTrue(result.event.all_day)

    def test_read_only_calendar_fails_closed_before_any_request(self) -> None:
        ref = EventRef(calendar_id="guardian-a", resource_name="anything.ics")
        base = EventBaseVersion(version=EventVersion('"e1"'), sequence=0)
        self.fx.requests.clear()

        for result in (
            self.fx.adapter.update_event(
                UpdateCalendarEventProposal(
                    event_ref=ref,
                    base_version=base,
                    changes=CalendarEventChanges(title="x"),
                ),
                operation_id="u",
            ),
            self.fx.adapter.cancel_event(
                CancelCalendarEventProposal(event_ref=ref, base_version=base),
                operation_id="c",
            ),
        ):
            self.assertEqual(result.status, CalendarChangeStatus.REJECTED)
            self.assertEqual(result.error_code, "calendar_not_writable")
        self.assertEqual(self.fx.requests, [])

    def test_unconfigured_calendar_fails_closed_before_any_request(self) -> None:
        event = self.fx.create()
        assert event.version is not None
        proposal = CancelCalendarEventProposal(
            event_ref=EventRef(calendar_id="nope", resource_name="x.ics"),
            base_version=base_of(event),
        )
        self.fx.requests.clear()
        result = self.fx.adapter.cancel_event(proposal, operation_id="c")
        self.assertEqual(result.error_code, "calendar_not_configured")
        self.assertEqual(self.fx.requests, [])

    def test_resource_name_cannot_escape_the_collection(self) -> None:
        event = self.fx.create()
        self.fx.requests.clear()
        for name in ("../other/x.ics", "a/b.ics", ".hidden", "x.ics?y=1", "x%2F.ics"):
            proposal = CancelCalendarEventProposal(
                event_ref=EventRef(calendar_id="family", resource_name=name),
                base_version=base_of(event),
            )
            result = self.fx.adapter.cancel_event(proposal, operation_id="c")
            self.assertEqual(result.error_code, "invalid_resource_name", name)
        self.assertEqual(self.fx.requests, [])


class CalDAVProfileCapabilityTests(unittest.TestCase):
    def test_capabilities_are_declared_per_operation_kind(self) -> None:
        fx = _Fixture()
        self.addCleanup(fx.adapter.close)
        self.assertEqual(fx.adapter.update_capability, IONOS_PROFILE.update_capability)
        self.assertEqual(fx.adapter.cancel_capability, IONOS_PROFILE.cancel_capability)


if __name__ == "__main__":
    unittest.main()
