from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timezone

from ada.adapters.caldav.dav_client import (
    CalDAVNotAttemptedError,
    CalDAVProtocolError,
    CalDAVResponseTooLargeError,
    CalDAVUnsafeXmlError,
)
from ada.adapters.caldav.mapping import CalendarComplexityExceededError
from ada.adapters.caldav.profile import IONOS_PROFILE
from caldav_test_support import FAMILY_PATH, build_adapter, build_fake_server


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
        server.force_redirect = True
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


if __name__ == "__main__":
    unittest.main()
