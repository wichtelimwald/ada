from __future__ import annotations

import unittest
from datetime import datetime, timezone

import httpx2

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.mapping import (
    build_create_ical,
    derive_event_uid,
    derive_operation_marker,
    derive_resource_name,
)
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

    return _adapter_with_method_override("PUT", exc)


def _adapter_with_method_override(
    method: str, override: Exception | httpx2.Response
) -> tuple[CalDAVCalendarAdapter, object]:
    """An adapter where one HTTP method either raises or returns a fixed
    response; every other method is served by a real, working fake server.
    """

    server = build_fake_server()

    def dispatch(request: httpx2.Request) -> httpx2.Response:
        if request.method == method:
            if isinstance(override, Exception):
                raise override
            return override
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

    def test_redirect_after_put_is_ambiguous_not_not_attempted(self) -> None:
        # The PUT was already sent and a response was received; a 3xx here
        # is not evidence that nothing happened. It must be reconciled, not
        # reported as a safe "not attempted" no-op.
        adapter, _server = _adapter_with_method_override(
            "PUT",
            httpx2.Response(
                302,
                headers={"Location": f"{BASE_URL}/elsewhere"},
            ),
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(_proposal(), operation_id="op-put-redirected")

        self.assertEqual(result.status, CalendarCreateStatus.AMBIGUOUS)

    def test_read_back_success_after_2xx_reports_committed_with_verified_event(
        self,
    ) -> None:
        # The ordinary path: 2xx PUT, then a successful read-back. Both the
        # deterministic reference and the provider-verified event are
        # available.
        server = build_fake_server()
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)
        proposal = _proposal()

        result = adapter.create_event(proposal, operation_id="op-readback-succeeds")

        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)
        assert result.event_ref is not None
        self.assertEqual(result.event_ref.calendar_id, "family")
        self.assertEqual(
            result.event_ref.resource_name,
            derive_resource_name("op-readback-succeeds"),
        )
        assert result.event is not None
        self.assertEqual(result.event.title, proposal.title)
        self.assertIsNotNone(result.event.version)

    def test_read_back_failure_after_2xx_still_reports_committed(self) -> None:
        # ADR-0009 section 6: "Any 2xx status is success" -- the provider
        # already committed the write. Ada's own read-back GET then fails,
        # but that is a verification problem, not evidence the write didn't
        # happen: it must not escape as a raw exception, and must not
        # downgrade an already-known commit to ambiguous. The provider owns
        # events, though: without a successful read-back Ada may only report
        # the deterministic reference it already knows, never the proposal
        # data as if it were verified provider state.
        proposal = _proposal()
        adapter, _server = _adapter_with_method_override(
            "GET", httpx2.ReadTimeout("simulated failure reading back the event")
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(proposal, operation_id="op-readback-fails")

        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)
        assert result.event_ref is not None
        self.assertEqual(result.event_ref.calendar_id, "family")
        self.assertEqual(
            result.event_ref.resource_name, derive_resource_name("op-readback-fails")
        )
        self.assertIsNone(result.event)

    def test_read_back_returning_not_found_after_2xx_still_reports_committed(
        self,
    ) -> None:
        # The provider says the write succeeded (2xx) but an immediate GET
        # reports the resource missing. The 2xx is still the evidence that
        # matters; this must not be reinterpreted as ambiguous either, and
        # (as above) Ada may only report the deterministic reference, not a
        # claimed verified event.
        proposal = _proposal()
        server = build_fake_server()

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            if request.method == "GET":
                return httpx2.Response(404, content=b"not found")
            return server(request)

        adapter = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(default_family_ref(),),
            profile=IONOS_PROFILE,
            transport=httpx2.MockTransport(dispatch),
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(
            proposal, operation_id="op-readback-not-found"
        )

        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)
        assert result.event_ref is not None
        self.assertEqual(
            result.event_ref.resource_name,
            derive_resource_name("op-readback-not-found"),
        )
        self.assertIsNone(result.event)

    def test_put_response_body_read_failure_still_reports_committed(self) -> None:
        # The create path never uses the PUT response body -- once the 201
        # status/headers are known, ADR-0009 section 6 already proves the
        # commit. A failure while streaming that (unused) body must not be
        # able to turn a known commit into anything weaker or raise a raw
        # exception.
        server = build_fake_server()
        server.put_response_body_read_failure = httpx2.ReadTimeout(
            "simulated failure while streaming the PUT response body"
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        result = adapter.create_event(
            _proposal(), operation_id="op-put-body-read-fails"
        )

        self.assertEqual(result.status, CalendarCreateStatus.COMMITTED)
        assert result.event_ref is not None
        self.assertEqual(
            result.event_ref.resource_name,
            derive_resource_name("op-put-body-read-fails"),
        )

    def test_reconciliation_failure_after_412_is_ambiguous(self) -> None:
        # PUT gets 412 (someone/something already created it); the
        # reconciling GET then fails too. This must not escape as a raw
        # exception either.
        operation_id = "op-412-reconcile-fails"
        marker = derive_operation_marker(operation_id)
        uid = derive_event_uid(operation_id)
        resource_name = derive_resource_name(operation_id)
        body = build_create_ical(_proposal(), uid=uid, marker=marker)

        server = build_fake_server()
        server.seed_resource(FAMILY_PATH, resource_name, body)

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            if request.method == "GET":
                raise httpx2.ReadTimeout("simulated failure during reconciliation")
            return server(request)

        adapter = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(default_family_ref(),),
            profile=IONOS_PROFILE,
            transport=httpx2.MockTransport(dispatch),
        )
        self.addCleanup(adapter.close)

        result = adapter.create_event(_proposal(), operation_id=operation_id)

        self.assertEqual(result.status, CalendarCreateStatus.AMBIGUOUS)
        self.assertEqual(result.error_code, "precondition_failed_unresolved")


if __name__ == "__main__":
    unittest.main()
