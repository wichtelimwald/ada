from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx2

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.dav_client import (
    CalDAVConfigurationError,
    CalDAVNotAttemptedError,
    CalDAVProtocolError,
    CalDAVResponseTooLargeError,
    CalDAVUnsafeXmlError,
    format_time_range_bound,
)
from ada.adapters.caldav.mapping import (
    CalendarComplexityExceededError,
    FloatingTimeNotSupportedError,
)
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef
from caldav_test_support import (
    BASE_URL,
    FAKE_AUTH,
    FAMILY_PATH,
    build_adapter,
    build_fake_server,
)


def _ical(uid: str, body: str) -> bytes:
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"{body}"
        "SEQUENCE:0\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    ).encode("utf-8")


class CalDAVReadPathTests(unittest.TestCase):
    def test_query_window_is_clamped_to_the_profile_bounds(self) -> None:
        server = build_fake_server()
        now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        adapter = build_adapter(server, clock=lambda: now)
        self.addCleanup(adapter.close)

        adapter.list_events(
            start=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(server.received_time_ranges), 2)  # two configured calendars
        clamped_start, clamped_end = server.received_time_ranges[0]
        self.assertEqual(clamped_start, now - IONOS_PROFILE.query_window_before)
        self.assertEqual(clamped_end, now + IONOS_PROFILE.query_window_after)

    def test_propfind_exposes_reported_privileges_for_the_startup_cross_check(
        self,
    ) -> None:
        # S2 scope is fetching/parsing privileges via PROPFIND; comparing
        # them against the configured access mode and failing closed is S6
        # ("ada doctor" startup checks). This proves the data S6 will need is
        # already correctly parsed.
        server = build_fake_server()
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        adapter.list_events(
            start=datetime(2026, 10, 1, tzinfo=timezone.utc),
            end=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )

        writable = adapter._collection_cache["family"]
        read_only = adapter._collection_cache["guardian-a"]
        self.assertEqual(writable.privileges, frozenset({"read", "write"}))
        self.assertEqual(read_only.privileges, frozenset({"read"}))

    def test_report_entity_tag_is_normalized_to_quoted_form(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "seeded.ics",
            _ical(
                "seeded-1@example",
                "DTSTART:20261012T160000Z\r\nDTEND:20261012T163000Z\r\n"
                "SUMMARY:Seeded event\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        events = adapter.list_events(
            start=datetime(2026, 10, 1, tzinfo=timezone.utc),
            end=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(events), 1)
        assert events[0].version is not None
        self.assertTrue(events[0].version.startswith('"'))
        self.assertTrue(events[0].version.endswith('"'))

    def test_recurrence_expansion_returns_each_occurrence_in_window(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "weekly.ics",
            _ical(
                "weekly-1@example",
                "DTSTART:20261001T090000Z\r\nDTEND:20261001T093000Z\r\n"
                "SUMMARY:Weekly meeting\r\nRRULE:FREQ=WEEKLY;COUNT=5\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        events = adapter.list_events(
            start=datetime(2026, 10, 1, tzinfo=timezone.utc),
            end=datetime(2026, 10, 22, tzinfo=timezone.utc),
        )

        self.assertEqual(len(events), 3)
        self.assertTrue(all(event.recurring for event in events))
        self.assertEqual(len({event.event_id for event in events}), 3)

    def test_all_day_event_is_mapped_with_the_all_day_flag(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "allday.ics",
            _ical(
                "allday-1@example",
                "DTSTART;VALUE=DATE:20261015\r\nDTEND;VALUE=DATE:20261016\r\n"
                "SUMMARY:All day\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        events = adapter.list_events(
            start=datetime(2026, 10, 1, tzinfo=timezone.utc),
            end=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].all_day)
        self.assertTrue(events[0].busy)  # TRANSP absent defaults to OPAQUE/busy

    def test_pathological_recurrence_fails_closed(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "pathological.ics",
            _ical(
                "pathological-1@example",
                "DTSTART:20261001T090000Z\r\nDTEND:20261001T093000Z\r\n"
                "SUMMARY:Pathological\r\nRRULE:FREQ=SECONDLY\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalendarComplexityExceededError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 10, 2, tzinfo=timezone.utc),
            )

    def test_too_many_properties_per_component_fails_closed(self) -> None:
        attendees = "".join(
            f"ATTENDEE:mailto:person{i}@example.test\r\n" for i in range(20)
        )
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "crowded.ics",
            _ical(
                "crowded-1@example",
                "DTSTART:20261012T160000Z\r\nDTEND:20261012T163000Z\r\n"
                f"SUMMARY:Crowded\r\n{attendees}",
            ),
        )
        tight_profile = dataclasses.replace(
            IONOS_PROFILE, max_properties_per_component=5
        )
        adapter = build_adapter(server, profile=tight_profile)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalendarComplexityExceededError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_too_many_components_per_response_fails_closed(self) -> None:
        server = build_fake_server()
        for index in range(3):
            server.seed_resource(
                FAMILY_PATH,
                f"event-{index}.ics",
                _ical(
                    f"event-{index}@example",
                    "DTSTART:20261012T160000Z\r\nDTEND:20261012T163000Z\r\n"
                    "SUMMARY:Ordinary\r\n",
                ),
            )
        tight_profile = dataclasses.replace(
            IONOS_PROFILE, max_components_per_response=2
        )
        adapter = build_adapter(server, profile=tight_profile)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalendarComplexityExceededError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_doctype_response_is_rejected(self) -> None:
        server = build_fake_server()
        server.inject_doctype = True
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVUnsafeXmlError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_oversized_response_is_rejected(self) -> None:
        server = build_fake_server()
        server.oversized_body = b"x" * (IONOS_PROFILE.max_response_bytes + 1)
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVResponseTooLargeError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_wrong_origin_href_is_rejected(self) -> None:
        server = build_fake_server()
        server.wrong_origin_href = "https://evil.example.test/hijacked/"
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVProtocolError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_redirect_response_is_never_followed(self) -> None:
        server = build_fake_server()
        server.force_redirect_methods = frozenset({"PROPFIND", "REPORT"})
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVNotAttemptedError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_malformed_icalendar_does_not_silently_succeed(self) -> None:
        server = build_fake_server()
        collection = server._collections[FAMILY_PATH]  # test-only introspection
        resource_path = f"{collection.canonical_href.rstrip('/')}/broken.ics"
        from caldav_fake_ionos_server import _StoredResource

        collection.resources[resource_path] = _StoredResource(
            body=b"this is not iCalendar data", uid="broken"
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(Exception):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_cross_origin_configured_collection_sends_no_request(self) -> None:
        """A misconfigured/malicious absolute collection URL on another
        origin must be rejected before anything is sent — including the
        Basic Auth header — not merely after a server-reported href is
        checked."""

        calls: list[httpx2.Request] = []

        def dispatch(request: httpx2.Request) -> httpx2.Response:
            calls.append(request)
            raise AssertionError("no request should ever reach the transport")

        cross_origin_ref = CalendarRef(
            calendar_id="family",
            provider_collection="https://evil.example.test/hijacked/",
            audience=CalendarAudience.FAMILY,
            access_mode=CalendarAccessMode.WRITE,
        )
        adapter = CalDAVCalendarAdapter(
            base_url=BASE_URL,
            auth=FAKE_AUTH,
            calendars=(cross_origin_ref,),
            profile=IONOS_PROFILE,
            transport=httpx2.MockTransport(dispatch),
        )
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVProtocolError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

        self.assertEqual(calls, [])

    def test_oversized_streaming_response_without_content_length_is_rejected(
        self,
    ) -> None:
        server = build_fake_server()
        server.stream_oversized_without_content_length = True
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalDAVResponseTooLargeError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

        # Proves the cap aborted an in-progress read rather than checking an
        # already fully materialized body: far fewer chunks were yielded
        # than the stream could have produced, and the stream was closed.
        stream = server.last_unbounded_stream
        assert stream is not None
        self.assertLess(
            stream.chunks_yielded * 4096, IONOS_PROFILE.max_response_bytes + 4096 * 2
        )
        self.assertTrue(stream.closed)

    def test_daily_rule_with_byhour_byminute_bysecond_fails_closed(self) -> None:
        # Before the fix, a DAILY period was treated as producing at most
        # one occurrence per day regardless of BY* parts, so a large COUNT
        # would be clamped down to "days in the window" (a handful) and
        # pass. BYHOUR/BYMINUTE/BYSECOND actually multiply each day out to
        # thousands of real occurrences, which COUNT alone still bounds
        # correctly once the per-day multiplication is accounted for.
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "adversarial.ics",
            _ical(
                "adversarial-1@example",
                "DTSTART:20261001T000000Z\r\nDTEND:20261001T000001Z\r\n"
                "SUMMARY:Adversarial\r\n"
                "RRULE:FREQ=DAILY;COUNT=50000;"
                "BYHOUR=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,"
                "21,22,23;"
                "BYMINUTE=0,15,30,45;"
                "BYSECOND=0,30\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(CalendarComplexityExceededError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 10, 3, tzinfo=timezone.utc),
            )

    def _seed_raw_resource(
        self, server, resource_name: str, body: bytes
    ) -> None:
        """Seed a resource whose raw bytes are exactly as given.

        Unlike ``server.seed_resource``, this allows more than one VEVENT
        component bundled into a single CalDAV resource, matching how a
        recurring series (a master plus its own overrides) is naturally
        represented, and how a resource with several unrelated masters
        would appear.
        """

        from caldav_fake_ionos_server import _StoredResource

        collection = server._collections[FAMILY_PATH]
        resource_path = f"{collection.canonical_href.rstrip('/')}/{resource_name}"
        collection.resources[resource_path] = _StoredResource(
            body=body, uid="test-only-multi-vevent-resource"
        )

    def test_query_budget_is_enforced_before_any_series_is_expanded(self) -> None:
        # One resource bundling three separate masters (distinct UIDs), each
        # individually well within max_occurrences_per_series, but their sum
        # exceeds a tight remaining per-query budget. ADR-0009 requires this
        # to fail closed *before* recurring_ical_events ever runs for this
        # resource, not merely after expanding it.
        body = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//\r\n"
            + "".join(
                f"BEGIN:VEVENT\r\nUID:multi-master-{i}@example\r\n"
                "DTSTART:20261001T090000Z\r\nDTEND:20261001T093000Z\r\n"
                f"SUMMARY:Series {i}\r\nRRULE:FREQ=DAILY;COUNT=5\r\n"
                "SEQUENCE:0\r\nEND:VEVENT\r\n"
                for i in range(3)
            )
            + "END:VCALENDAR\r\n"
        ).encode("utf-8")

        server = build_fake_server()
        self._seed_raw_resource(server, "multi-master.ics", body)
        tight_profile = dataclasses.replace(
            IONOS_PROFILE, max_occurrences_per_query=10
        )
        adapter = build_adapter(server, profile=tight_profile)
        self.addCleanup(adapter.close)

        with patch(
            "ada.adapters.caldav.mapping.recurring_ical_events.of",
            side_effect=AssertionError("expansion must not run past the budget"),
        ):
            with self.assertRaises(CalendarComplexityExceededError):
                adapter.list_events(
                    start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    end=datetime(2026, 11, 1, tzinfo=timezone.utc),
                )

    def test_component_budget_is_enforced_before_any_series_is_expanded(self) -> None:
        # One resource bundling three ordinary (non-recurring) VEVENTs, over
        # a tight remaining per-response component budget.
        body = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//\r\n"
            + "".join(
                f"BEGIN:VEVENT\r\nUID:plain-{i}@example\r\n"
                "DTSTART:20261012T160000Z\r\nDTEND:20261012T163000Z\r\n"
                "SUMMARY:Ordinary\r\nSEQUENCE:0\r\nEND:VEVENT\r\n"
                for i in range(3)
            )
            + "END:VCALENDAR\r\n"
        ).encode("utf-8")

        server = build_fake_server()
        self._seed_raw_resource(server, "plain-bundle.ics", body)
        tight_profile = dataclasses.replace(
            IONOS_PROFILE, max_components_per_response=2
        )
        adapter = build_adapter(server, profile=tight_profile)
        self.addCleanup(adapter.close)

        with patch(
            "ada.adapters.caldav.mapping.recurring_ical_events.of",
            side_effect=AssertionError("expansion must not run past the budget"),
        ):
            with self.assertRaises(CalendarComplexityExceededError):
                adapter.list_events(
                    start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    end=datetime(2026, 11, 1, tzinfo=timezone.utc),
                )

    def test_format_time_range_bound_converts_to_utc(self) -> None:
        plus_two = datetime(2026, 10, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(format_time_range_bound(plus_two), "20261001T080000Z")

    def test_format_time_range_bound_rejects_naive_input(self) -> None:
        with self.assertRaises(CalDAVConfigurationError):
            format_time_range_bound(datetime(2026, 10, 1, 10, 0))

    def test_query_window_non_utc_input_is_converted_before_being_sent(self) -> None:
        server = build_fake_server()
        now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        adapter = build_adapter(server, clock=lambda: now)
        self.addCleanup(adapter.close)

        # A start later than the clamped floor is used as-is by max(), so its
        # own (non-UTC) tzinfo must be converted before formatting, or the
        # sent time-range silently shifts by the offset.
        non_utc_start = datetime(
            2026, 10, 5, 10, 0, tzinfo=timezone(timedelta(hours=2))
        )
        adapter.list_events(
            start=non_utc_start,
            end=non_utc_start + timedelta(hours=1),
        )

        clamped_start, _ = server.received_time_ranges[0]
        self.assertEqual(clamped_start, non_utc_start.astimezone(timezone.utc))

    def test_floating_datetime_fails_closed(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "floating.ics",
            _ical(
                "floating-1@example",
                "DTSTART:20261012T160000\r\nDTEND:20261012T163000\r\n"
                "SUMMARY:Floating\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        with self.assertRaises(FloatingTimeNotSupportedError):
            adapter.list_events(
                start=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end=datetime(2026, 11, 1, tzinfo=timezone.utc),
            )

    def test_all_day_event_without_dtend_gets_implicit_one_day_duration(
        self,
    ) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH,
            "allday-no-dtend.ics",
            _ical(
                "allday-no-dtend-1@example",
                "DTSTART;VALUE=DATE:20261015\r\nSUMMARY:All day, no DTEND\r\n",
            ),
        )
        adapter = build_adapter(server)
        self.addCleanup(adapter.close)

        events = adapter.list_events(
            start=datetime(2026, 10, 1, tzinfo=timezone.utc),
            end=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].all_day)
        self.assertEqual(
            events[0].end - events[0].start, timedelta(days=1)
        )


if __name__ == "__main__":
    unittest.main()
