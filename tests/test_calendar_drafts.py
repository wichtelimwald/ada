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
            calendar_id="family",
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

    def test_complete_draft_still_does_not_claim_execution(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Dentist appointment",
            date="2026-09-21",
            start_time="16:00",
            end_time="16:30",
            calendar_id="family",
            language="en",
        )

        assessment = assess_calendar_create_draft(draft)
        response = render_calendar_draft_response(draft)

        self.assertTrue(assessment.complete)
        self.assertIn("draft", response)
        self.assertIn("have not changed the calendar", response)

    def test_unresolved_model_fields_are_preserved(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Dentist appointment",
            date="2026-09-21",
            start_time="16:00",
            end_time="16:30",
            calendar_id="family",
            language="en",
            unresolved=("participant",),
        )

        assessment = assess_calendar_create_draft(draft)

        self.assertEqual(assessment.missing, ("participant",))


if __name__ == "__main__":
    unittest.main()
