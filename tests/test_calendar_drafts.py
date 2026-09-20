from __future__ import annotations

import unittest

from ada.application.calendar_drafts import (
    assess_calendar_create_draft,
    render_calendar_draft_response,
)
from ada.core.actions import CreateCalendarEventDraft


class CalendarDraftTests(unittest.TestCase):
    def test_partial_german_calendar_request_stays_non_executable(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Zahnarzt",
            date="21.09.",
            start_time="16:00",
            end_time=None,
            calendar_id="family",
            location=None,
            language="de",
            unresolved=("year", "end_time"),
        )

        assessment = assess_calendar_create_draft(draft)
        response = render_calendar_draft_response(draft)

        self.assertFalse(assessment.complete)
        self.assertIn("date_with_year", assessment.missing)
        self.assertIn("end_time", assessment.missing)
        self.assertIn("noch nichts in den Kalender eingetragen", response)
        self.assertIn("vollständiges Datum mit Jahr", response)
        self.assertIn("Endzeit oder Dauer", response)

    def test_model_cannot_invent_missing_year_from_partial_source(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Zahnarzt",
            date="2026-09-21",
            start_time="16:00",
            end_time=None,
            calendar_id="family",
            location=None,
            language="de",
            unresolved=("end_time", "location", "dentist_name"),
        )

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Kannst du einen Zahnarzttermin am 21.09. für 16:00 Uhr "
                "in den Familienkalender eintragen?"
            ),
        )
        response = render_calendar_draft_response(
            draft,
            source_text=(
                "Kannst du einen Zahnarzttermin am 21.09. für 16:00 Uhr "
                "in den Familienkalender eintragen?"
            ),
        )

        self.assertEqual(
            assessment.missing,
            ("date_with_year", "end_time"),
        )
        self.assertIn("vollständiges Datum mit Jahr", response)
        self.assertIn("Endzeit oder Dauer", response)
        self.assertNotIn("location", response)
        self.assertNotIn("Zahnarztname", response)

    def test_complete_draft_still_does_not_claim_execution(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Dentist appointment",
            date="2026-09-21",
            start_time="16:00",
            end_time="16:30",
            calendar_id="family",
            location=None,
            language="en",
            unresolved=(),
        )

        assessment = assess_calendar_create_draft(draft)
        response = render_calendar_draft_response(draft)

        self.assertTrue(assessment.complete)
        self.assertIn("draft", response)
        self.assertIn("have not changed the calendar", response)

    def test_arbitrary_model_unresolved_fields_do_not_become_requirements(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Dentist appointment",
            date="2026-09-21",
            start_time="16:00",
            end_time="16:30",
            calendar_id="family",
            location=None,
            language="en",
            unresolved=("participant", "location", "dentist_name", "specialty"),
        )

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Please add a dentist appointment on 2026-09-21 "
                "from 16:00 to 16:30 to the family calendar."
            ),
        )

        self.assertEqual(assessment.missing, ())


if __name__ == "__main__":
    unittest.main()
