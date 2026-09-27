from __future__ import annotations

import unittest
from datetime import datetime, timezone

import httpx2

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.mapping import build_create_ical, derive_event_uid
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import CalendarCreateStatus
from caldav_test_support import (
    BASE_URL,
    FAKE_AUTH,
    FAMILY_PATH,
    build_adapter,
    build_fake_server,
    default_family_ref,
)


def _proposal(**overrides: object) -> CreateCalendarEventProposal:
    defaults: dict[str, object] = {
        "title": "Parent-teacher meeting",
        "start": datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        "end": datetime(2026, 10, 12, 16, 30, tzinfo=timezone.utc),
        "calendar_id": "family",
        "location": "School North",
    }
    defaults.update(overrides)
    return CreateCalendarEventProposal(**defaults)  # type: ignore[arg-type]


def _adapter_with_put_failure(exc: Exception) -> tuple[CalDAVCalendarAdapter, object]:
    """An adapter whose PUT raises ``exc``; other methods use a real fake server."""

    server = build_fake_server()

    def dispatch(request: httpx2.Request) -> httpx2.Response:
        if request.method == "PUT":
            raise exc
        return server(request)

    adapter = CalDAVCalendarAdapter(
        base_url=BASE_URL,
        auth=FAKE_AUTH,
        calendars=(default_family_ref(),),
        profile=IONOS_PROFILE,
        transport=httpx2.MockTransport(dispatch),
    )
    return adapter, server


class CalDAVCreateTests(unittest.TestCase):
    def test_read_only_calendar_rejects_create_without_any_request(self) -> None:
        server = build_fake_server()
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        result = adapter.create_event(
            _proposal(calendar_id="guardian-a"),
            operation_id="op-read-only-target",
        )

        self.assertEqual(result.status, CalendarCreateStatus.REJECTED)
        self.assertEqual(result.error_code, "calendar_not_writable")
        self.assertEqual(server.put_attempts, 0)

    def test_unconfigured_calendar_rejects_create_without_any_request(self) -> None:
        server = build_fake_server()
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        result = adapter.create_event(
            _proposal(calendar_id="unknown-calendar"),
            operation_id="op-unconfigured-target",
        )

        self.assertEqual(result.status, CalendarCreateStatus.REJECTED)
        self.assertEqual(result.error_code, "calendar_not_configured")
        self.assertEqual(server.put_attempts, 0)

    def test_duplicate_uid_under_a_different_resource_is_ambiguous(self) -> None:
        server = build_fake_server()
        operation_id = "op-duplicate-uid"
        conflicting_uid = derive_event_uid(operation_id)
        conflicting_body = build_create_ical(
            _proposal(), uid=conflicting_uid, marker="someone-elses-marker"
        )
        server.seed_resource(
            FAMILY_PATH, "pre-existing-different-name.ics", conflicting_body
        )

        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        result = adapter.create_event(_proposal(), operation_id=operation_id)

        self.assertEqual(result.status, CalendarCreateStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "duplicate_uid_conflict")

    def test_ambiguous_transport_after_send_is_reported_as_ambiguous(self) -> None:
        adapter, _server = _adapter_with_put_failure(
            httpx2.ReadTimeout("simulated response loss after send")
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(
            _proposal(), operation_id="op-ambiguous-transport"
        )

        self.assertEqual(result.status, CalendarCreateStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "ambiguous_transport")

    def test_not_attempted_on_connection_failure(self) -> None:
        adapter, server = _adapter_with_put_failure(
            httpx2.ConnectError("simulated connection refused")
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(_proposal(), operation_id="op-not-attempted")

        self.assertEqual(result.status, CalendarCreateStatus.REJECTED)
        self.assertEqual(result.error_code, "not_attempted")
        self.assertEqual(server.put_attempts, 0)


if __name__ == "__main__":
    unittest.main()
