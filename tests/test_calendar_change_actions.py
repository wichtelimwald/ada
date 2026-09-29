from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timezone

from ada.core.actions import (
    CalendarEventChanges,
    CalendarProposalValidationError,
    CancelCalendarEventProposal,
    EventBaseVersion,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
    calendar_cancel_action_binding,
    calendar_update_action_binding,
    validate_calendar_cancel_proposal,
    validate_calendar_update_proposal,
)

REF = EventRef(calendar_id="family", resource_name="ada-1.ics")
BASE = EventBaseVersion(version=EventVersion('"e1"'), sequence=2)
T0 = datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 10, 12, 17, 0, tzinfo=timezone.utc)


def update(**overrides: object) -> UpdateCalendarEventProposal:
    fields: dict[str, object] = {
        "event_ref": REF,
        "base_version": BASE,
        "changes": CalendarEventChanges(title="New"),
    }
    fields.update(overrides)
    return UpdateCalendarEventProposal(**fields)  # type: ignore[arg-type]


class UpdateValidationTests(unittest.TestCase):
    def test_valid_update_passes(self) -> None:
        validate_calendar_update_proposal(update())
        validate_calendar_update_proposal(
            update(changes=CalendarEventChanges(start=T0, end=T1, location="Home"))
        )

    def test_invalid_updates_are_rejected(self) -> None:
        naive = datetime(2026, 10, 12, 16, 0)
        cases = {
            "no change": CalendarEventChanges(),
            "blank title": CalendarEventChanges(title="  "),
            "blank location": CalendarEventChanges(location=" "),
            "naive start": CalendarEventChanges(start=naive),
            "end before start": CalendarEventChanges(start=T1, end=T0),
        }
        for name, changes in cases.items():
            with self.subTest(name), self.assertRaises(CalendarProposalValidationError):
                validate_calendar_update_proposal(update(changes=changes))

    def test_event_target_is_required_and_sequence_non_negative(self) -> None:
        with self.assertRaises(CalendarProposalValidationError):
            validate_calendar_update_proposal(
                update(event_ref=EventRef(calendar_id="", resource_name="x"))
            )
        with self.assertRaises(CalendarProposalValidationError):
            validate_calendar_update_proposal(
                update(event_ref=EventRef(calendar_id="family", resource_name=" "))
            )
        with self.assertRaises(CalendarProposalValidationError):
            validate_calendar_update_proposal(
                update(base_version=EventBaseVersion(BASE.version, -1))
            )

    def test_cancel_validation(self) -> None:
        validate_calendar_cancel_proposal(
            CancelCalendarEventProposal(event_ref=REF, base_version=BASE)
        )
        with self.assertRaises(CalendarProposalValidationError):
            validate_calendar_cancel_proposal(
                CancelCalendarEventProposal(
                    event_ref=EventRef(calendar_id="family", resource_name=""),
                    base_version=BASE,
                )
            )


class ActionBindingTests(unittest.TestCase):
    def test_binding_is_stable(self) -> None:
        self.assertEqual(
            calendar_update_action_binding(update()),
            calendar_update_action_binding(update()),
        )

    def test_update_binding_changes_with_every_bound_field(self) -> None:
        reference = calendar_update_action_binding(update())
        variants = [
            update(changes=CalendarEventChanges(title="Other")),
            update(changes=CalendarEventChanges(title="New", location="Home")),
            update(changes=CalendarEventChanges(title="New", start=T0)),
            update(base_version=EventBaseVersion(EventVersion('"e2"'), 2)),
            update(base_version=EventBaseVersion(BASE.version, 3)),
            update(event_ref=EventRef("family", "ada-2.ics")),
            update(event_ref=EventRef("guardian-a", "ada-1.ics")),
        ]
        bindings = {calendar_update_action_binding(v) for v in variants}
        self.assertNotIn(reference, bindings)
        self.assertEqual(len(bindings), len(variants))

    def test_cancel_binding_covers_base_version_and_differs_from_update(self) -> None:
        cancel = CancelCalendarEventProposal(event_ref=REF, base_version=BASE)
        newer = dataclasses.replace(
            cancel, base_version=EventBaseVersion(EventVersion('"e2"'), 2)
        )
        self.assertNotEqual(
            calendar_cancel_action_binding(cancel),
            calendar_cancel_action_binding(newer),
        )
        self.assertTrue(
            calendar_cancel_action_binding(cancel).startswith("calendar.cancel:")
        )
        self.assertTrue(
            calendar_update_action_binding(update()).startswith("calendar.update:")
        )

    def test_binding_does_not_expose_content(self) -> None:
        binding = calendar_update_action_binding(
            update(changes=CalendarEventChanges(title="Secret dentist visit"))
        )
        self.assertNotIn("dentist", binding)


if __name__ == "__main__":
    unittest.main()
