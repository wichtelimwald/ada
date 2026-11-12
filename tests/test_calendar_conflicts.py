from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from ada.adapters.configured_travel_time import ConfiguredTravelTime
from ada.application.calendar_actions import (
    CalendarConflictChecker,
    ConflictKind,
    availability_for_conflicts,
)
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import CalendarBusyInterval, CalendarEvent


def instant(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


def candidate(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    location: str | None = "New Hall",
) -> CreateCalendarEventProposal:
    return CreateCalendarEventProposal(
        title="Test family appointment",
        start=start or instant(12, 16),
        end=end or instant(12, 17),
        calendar_id="family",
        location=location,
    )


def event(
    *,
    event_id: str = "provider-private-identifier",
    calendar_id: str = "family",
    start: datetime | None = None,
    end: datetime | None = None,
    location: str | None = "Old Hall",
    busy: bool = True,
    recurring: bool = False,
) -> CalendarEvent:
    return CalendarEvent(
        event_id=event_id,
        title="Confidential meeting details",
        start=start or instant(12, 15),
        end=end or instant(12, 15, 30),
        calendar_id=calendar_id,
        location=location,
        busy=busy,
        recurring=recurring,
    )


PLACES = {"Old Hall": "old", "New Hall": "new"}


class AvailabilityProjectionTests(unittest.TestCase):
    def test_private_details_never_enter_availability_intervals(self) -> None:
        slots = availability_for_conflicts(
            (event(),),
            relevant_calendar_ids={"family"},
            registered_places=PLACES,
        )
        self.assertEqual(
            slots,
            (
                CalendarBusyInterval(
                    slot_id="slot-1",
                    calendar_id="family",
                    start=instant(12, 15),
                    end=instant(12, 15, 30),
                    place_key="old",
                ),
            ),
        )
        self.assertNotIn("Confidential meeting", repr(slots))
        self.assertNotIn("Old Hall", repr(slots))
        self.assertNotIn("place_key", repr(slots))
        self.assertNotIn("provider-private-identifier", repr(slots))

    def test_transparent_and_unrelated_personal_events_are_excluded(self) -> None:
        slots = availability_for_conflicts(
            (
                event(event_id="transparent", busy=False),
                event(event_id="other-person", calendar_id="person-b"),
                event(event_id="family"),
                event(event_id="own", calendar_id="person-a"),
            ),
            relevant_calendar_ids={"person-a", "family"},
            registered_places=PLACES,
        )
        self.assertEqual(len(slots), 2)
        self.assertEqual([s.calendar_id for s in slots], ["family", "person-a"])

    def test_unregistered_location_does_not_leak_raw_provider_location(self) -> None:
        slots = availability_for_conflicts(
            (event(location="Sensitive home address"),),
            relevant_calendar_ids={"family"},
            registered_places=PLACES,
        )
        self.assertIsNone(slots[0].place_key)
        self.assertNotIn("Sensitive home address", repr(slots))


class ConfiguredTravelTimeTests(unittest.TestCase):
    def test_only_explicit_directional_routes_are_known(self) -> None:
        routes = ConfiguredTravelTime({("old", "new"): timedelta(minutes=25)})
        self.assertEqual(
            routes.estimate(origin="old", destination="new").duration,
            timedelta(minutes=25),
        )
        unknown = routes.estimate(origin="new", destination="old")
        self.assertIsNone(unknown.duration)
        self.assertEqual(unknown.source, "unconfigured")

    def test_invalid_routes_are_rejected(self) -> None:
        for routes in (
            {("", "school"): timedelta(minutes=5)},
            {("home", "school"): timedelta(minutes=-1)},
        ):
            with self.subTest(routes=routes), self.assertRaises(ValueError):
                ConfiguredTravelTime(routes)


class ConflictDetectionTests(unittest.TestCase):
    def checker(self) -> CalendarConflictChecker:
        return CalendarConflictChecker(
            ConfiguredTravelTime({("old", "new"): timedelta(minutes=45)})
        )

    def slots(self, *events: CalendarEvent) -> tuple[CalendarBusyInterval, ...]:
        return availability_for_conflicts(
            events,
            relevant_calendar_ids={"family", "person-a"},
            registered_places=PLACES,
        )

    def test_travel_conflict_from_configured_places(self) -> None:
        result = self.checker().check(
            candidate(),
            existing_events=self.slots(event()),
            candidate_place_key="new",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].kind, ConflictKind.TRAVEL_TIME)
        self.assertEqual(result[0].available_gap, timedelta(minutes=30))
        self.assertEqual(result[0].required_travel, timedelta(minutes=45))
        self.assertEqual(result[0].travel_source, "configured")
        self.assertEqual(result[0].slot_id, "slot-1")

    def test_known_route_with_enough_time_is_not_a_conflict(self) -> None:
        result = self.checker().check(
            candidate(start=instant(12, 17), end=instant(12, 18)),
            existing_events=self.slots(event()),
            candidate_place_key="new",
        )
        self.assertEqual(result, ())

    def test_missing_route_is_explicit_unknown_not_zero(self) -> None:
        result = self.checker().check(
            candidate(start=instant(12, 13), end=instant(12, 14)),
            existing_events=self.slots(event()),
            candidate_place_key="new",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].kind, ConflictKind.TRAVEL_UNKNOWN)
        self.assertEqual(result[0].travel_source, "unconfigured")
        self.assertIsNone(result[0].required_travel)

    def test_missing_registered_place_is_explicit_unknown(self) -> None:
        result = self.checker().check(
            candidate(),
            existing_events=self.slots(event(location="Secret address")),
            candidate_place_key="new",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].kind, ConflictKind.TRAVEL_UNKNOWN)
        self.assertEqual(result[0].travel_source, "place_not_registered")

    def test_overlapping_occurrence_is_detected_without_details(self) -> None:
        # The real CalDAV adapter expands weekly recurrence into separate
        # CalendarEvent intervals before this checker receives them.
        recurring = (
            event(start=instant(12, 15), end=instant(12, 15, 30), recurring=True),
            event(start=instant(19, 15), end=instant(19, 15, 30), recurring=True),
        )
        result = self.checker().check(
            candidate(start=instant(19, 15, 15), end=instant(19, 16)),
            existing_events=self.slots(*recurring),
            candidate_place_key="new",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].kind, ConflictKind.TIME_OVERLAP)
        self.assertEqual(result[0].slot_id, "slot-2")

    def test_transparent_event_never_causes_conflict(self) -> None:
        result = self.checker().check(
            candidate(start=instant(12, 15, 15), end=instant(12, 16)),
            existing_events=self.slots(event(busy=False)),
            candidate_place_key="new",
        )
        self.assertEqual(result, ())


if __name__ == "__main__":
    unittest.main()
