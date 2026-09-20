from __future__ import annotations

import unittest

from ada.application.calendar_drafts import (
    assess_calendar_create_draft,
    render_calendar_draft_response,
)
from ada.core.actions import CreateCalendarEventDraft


def _draft(
    *,
    title: str | None = "Dentist appointment",
    date: str | None = "2026-09-21",
    start_time: str | None = "16:00",
    end_time: str | None = "16:30",
    calendar_id: str | None = "family",
    language: str = "en",
    unresolved: tuple[str, ...] = (),
) -> CreateCalendarEventDraft:
    return CreateCalendarEventDraft(
        title=title,
        date=date,
        start_time=start_time,
        end_time=end_time,
        calendar_id=calendar_id,
        location=None,
        language=language,  # type: ignore[arg-type]
        unresolved=unresolved,
    )


class CalendarDraftTests(unittest.TestCase):
    def test_partial_german_calendar_request_stays_non_executable(self) -> None:
        draft = _draft(
            title="Zahnarzt",
            date="21.09.",
            start_time="16:00",
            end_time=None,
            calendar_id="family",
            language="de",
            unresolved=("year", "end_time"),
        )

        source = (
            "Kannst du einen Zahnarzttermin am 21.09. für 16:00 Uhr "
            "in den Familienkalender eintragen?"
        )
        assessment = assess_calendar_create_draft(
            draft,
            source_text=source,
        )
        response = render_calendar_draft_response(
            draft,
            source_text=source,
        )

        self.assertFalse(assessment.complete)
        self.assertIn("date_with_year", assessment.missing)
        self.assertIn("end_time", assessment.missing)
        self.assertIn("noch nichts in den Kalender eingetragen", response)
        self.assertIn("Datum mit Jahr", response)
        self.assertIn("Endzeit oder Dauer", response)

    def test_model_cannot_invent_missing_year_from_partial_source(self) -> None:
        draft = _draft(
            title="Zahnarzt",
            end_time=None,
            language="de",
            unresolved=("end_time", "location", "dentist_name"),
        )
        source = (
            "Kannst du einen Zahnarzttermin am 21.09. für 16:00 Uhr "
            "in den Familienkalender eintragen?"
        )

        assessment = assess_calendar_create_draft(draft, source_text=source)

        self.assertEqual(
            assessment.missing,
            ("date_with_year", "end_time"),
        )

    def test_unrelated_four_digit_number_does_not_validate_model_year(self) -> None:
        draft = _draft(
            title="Zahnarzt",
            date="2031-03-15",
            start_time="16:00",
            end_time="16:30",
            calendar_id="family",
            language="de",
        )
        source = (
            "Zahnarzttermin am 15.03. um 16:00 bis 16:30, "
            "Zimmer 2024, im Familienkalender."
        )

        assessment = assess_calendar_create_draft(draft, source_text=source)

        self.assertIn("date_with_year", assessment.missing)

    def test_different_explicit_date_does_not_validate_model_date(self) -> None:
        draft = _draft(date="2031-03-15")
        source = (
            "Please add a dentist appointment on 2026-03-15 "
            "from 16:00 to 16:30 to the family calendar."
        )

        assessment = assess_calendar_create_draft(draft, source_text=source)

        self.assertIn("date_with_year", assessment.missing)

    def test_valid_day_first_date_supports_model_date(self) -> None:
        draft = _draft(date="2026-09-21")
        source = (
            "Bitte den Zahnarzttermin am 21.09.2026 von 16:00 bis 16:30 "
            "in den Familienkalender eintragen."
        )

        assessment = assess_calendar_create_draft(draft, source_text=source)

        self.assertEqual(assessment.missing, ())

    def test_invalid_calendar_date_is_not_complete(self) -> None:
        for invalid in ("2026-02-30", "2026-13-01"):
            with self.subTest(invalid=invalid):
                draft = _draft(date=invalid)
                assessment = assess_calendar_create_draft(
                    draft,
                    source_text=(
                        f"Add the appointment on {invalid} from 16:00 to 16:30 "
                        "to the family calendar."
                    ),
                )
                self.assertIn("date_with_year", assessment.missing)
                self.assertFalse(assessment.complete)

    def test_end_time_must_be_after_start_time(self) -> None:
        draft = _draft(start_time="18:00", end_time="09:00")

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Add the appointment on 2026-09-21 from 18:00 to 09:00 "
                "to the family calendar."
            ),
        )

        self.assertIn("end_time", assessment.missing)
        self.assertFalse(assessment.complete)

    def test_missing_calendar_remains_material_requirement(self) -> None:
        draft = _draft(calendar_id=None)

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Add the dentist appointment on 2026-09-21 from 16:00 to 16:30."
            ),
        )

        self.assertEqual(assessment.missing, ("calendar",))

    def test_model_cannot_invent_nonempty_calendar_target(self) -> None:
        draft = _draft(
            calendar_id="family",
        )

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Please add the dentist appointment on 2026-09-21 "
                "from 16:00 to 16:30."
            ),
        )

        self.assertEqual(assessment.missing, ("calendar",))

    def test_unknown_calendar_id_is_not_accepted_even_if_nonempty(self) -> None:
        draft = _draft(
            calendar_id="work",
        )

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Please add the dentist appointment on 2026-09-21 "
                "from 16:00 to 16:30 to the work calendar."
            ),
        )

        self.assertEqual(assessment.missing, ("calendar",))

    def test_complete_draft_still_does_not_claim_execution(self) -> None:
        draft = _draft()

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Please add a dentist appointment on 2026-09-21 "
                "from 16:00 to 16:30 to the family calendar."
            ),
        )
        response = render_calendar_draft_response(
            draft,
            source_text=(
                "Please add a dentist appointment on 2026-09-21 "
                "from 16:00 to 16:30 to the family calendar."
            ),
        )

        self.assertTrue(assessment.complete)
        self.assertIn("draft", response)
        self.assertIn("have not changed the calendar", response)

    def test_arbitrary_model_unresolved_fields_do_not_become_requirements(self) -> None:
        draft = _draft(
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
