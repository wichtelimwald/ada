from __future__ import annotations

import unittest
from itertools import product

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
        self.assertIn("gültige Endzeit", response)

    def test_source_text_is_required_for_draft_assessment(self) -> None:
        draft = _draft()

        with self.assertRaises(TypeError):
            assess_calendar_create_draft(draft)  # type: ignore[call-arg]

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

    def test_two_digit_year_does_not_corroborate_model_century(self) -> None:
        draft = _draft(date="2126-09-21")

        assessment = assess_calendar_create_draft(
            draft,
            source_text=(
                "Bitte den Zahnarzttermin am 21.09.26 von 16:00 bis 16:30 "
                "in den Familienkalender eintragen."
            ),
        )

        self.assertIn("date_with_year", assessment.missing)

    def test_valid_day_first_date_supports_model_date(self) -> None:
        draft = _draft(date="2026-09-21")
        source = (
            "Bitte den Zahnarzttermin am 21.09.2026 von 16:00 bis 16:30 "
            "in den Familienkalender eintragen."
        )

        assessment = assess_calendar_create_draft(draft, source_text=source)

        self.assertEqual(assessment.missing, ())

    def test_written_german_month_supports_explicit_date(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(date="2026-10-12", language="de"),
            source_text=(
                "Zahnarzttermin am 12. Oktober 2026 von 16 Uhr bis 16:30 "
                "in den Familienkalender eintragen."
            ),
        )
        self.assertEqual(assessment.missing, ())

    def test_model_cannot_invent_start_or_end_time(self) -> None:
        source = (
            "Please add a dentist appointment on 2026-09-21 at 16:00 "
            "to the family calendar."
        )
        assessment = assess_calendar_create_draft(
            _draft(start_time="15:00", end_time="16:30"),
            source_text=source,
        )
        self.assertEqual(assessment.missing, ("start_time", "end_time"))

    def test_model_cannot_invent_end_time_for_explicit_start(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(end_time="16:30"),
            source_text=(
                "Please add a dentist appointment on 2026-09-21 at 16:00 "
                "to the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ("end_time",))

    def test_time_cannot_match_prefix_of_more_precise_source_time(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(start_time="16:00", end_time="16:30"),
            source_text=(
                "Please add a dentist appointment on 2026-09-21 from "
                "16:00:30 to 16:30:45 to the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ("start_time", "end_time"))

    def test_dotted_date_components_do_not_corroborate_time(self) -> None:
        for source_date in ("2026.09.21", "2026-09.21", "2026/09.21"):
            with self.subTest(source_date=source_date):
                assessment = assess_calendar_create_draft(
                    _draft(date="2026-09-21", start_time="09:21", end_time="10:00"),
                    source_text=(
                        f"Add a dentist appointment on {source_date} "
                        "at 10:00 to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time",))

    def test_explicit_dotted_time_still_supports_draft(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(date="2026-09-21", start_time="09:21", end_time="10:00"),
            source_text=(
                "Add a dentist appointment on 2026-09.21 "
                "from 09.21 to 10:00 to the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ())

    def test_two_digit_year_date_does_not_corroborate_time(self) -> None:
        for source_date in ("21.09.26", "21-09.26", "21/09.26", "21 . 09.26"):
            with self.subTest(source_date=source_date):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="09:26", end_time="10:00"),
                    source_text=(
                        f"Add a dentist appointment on {source_date} "
                        "at 10:00 to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ("date_with_year", "start_time"))

    def test_two_digit_year_mask_preserves_separate_dotted_time(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(start_time="09:26", end_time="10:00"),
            source_text=(
                "Add a dentist appointment on 21-09.26 "
                "from 09.26 to 10:00 to the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ("date_with_year",))

    def test_invalid_times_are_missing_without_source_parsing(self) -> None:
        source = (
            "Add a dentist appointment on 2026-09-21 "
            "to the family calendar."
        )
        for invalid in (None, "six pm", "25:00", "16:0"):
            with self.subTest(invalid=invalid):
                assessment = assess_calendar_create_draft(
                    _draft(start_time=invalid, end_time=invalid),
                    source_text=source,
                )
                self.assertEqual(assessment.missing, ("start_time", "end_time"))

    def test_partial_dates_in_both_orders_do_not_corroborate_dotted_times(self) -> None:
        for source_date, start_time in (
            ("21.09.", "21:09"),
            ("21.09", "21:09"),
            ("21 . 09.", "21:09"),
            ("09.21", "09:21"),
            ("09.21.", "09:21"),
            ("12.31", "12:31"),
        ):
            with self.subTest(source_date=source_date):
                assessment = assess_calendar_create_draft(
                    _draft(start_time=start_time, end_time="22:00"),
                    source_text=(
                        f"Add a dentist appointment on {source_date} "
                        "to 22:00 to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ("date_with_year", "start_time"))

    def test_month_first_partial_date_standalone_does_not_corroborate_time(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(start_time="09:21", end_time="10:00"),
            source_text=(
                "Add a dentist appointment on 09.21 ending at 10:00 "
                "in the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ("date_with_year", "start_time"))

    def test_unambiguous_standalone_dotted_time_still_supports_draft(self) -> None:
        assessment = assess_calendar_create_draft(
            _draft(start_time="16:30", end_time="17:00"),
            source_text=(
                "Add a dentist appointment on 2026-09-21 at 16.30, "
                "ending at 17:00 in the family calendar."
            ),
        )
        self.assertEqual(assessment.missing, ())

    def test_compact_time_ranges_are_not_masked_as_dates(self) -> None:
        for time_range in (
            "16.30-17.00", "16.30–17.00", "16.30 - 17:00",
            "16:30-17.00", "16.30-17.00.",
        ):
            with self.subTest(time_range=time_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="16:30", end_time="17:00"),
                    source_text=(
                        "Add a dentist appointment on 2026-09-21 "
                        f"from {time_range} to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ())

    def test_ambiguous_dotted_date_ranges_require_a_time_marker(self) -> None:
        for time_range in (
            "09.10-10.11", "09.10–10.11", "09.10. bis 10.11.",
            "09.21-10.22", "09.21 to 10.22", "09.10-10.30", "09.10 to 10.30",
        ):
            with self.subTest(time_range=time_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="09:10", end_time="10:11"),
                    source_text=(
                        "Add a dentist appointment on 2026-09-21 "
                        f"from {time_range} to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time", "end_time"))

        for time_range in ("09.10-10.11 Uhr", "09.10 Uhr bis 10.11 Uhr", "09:10-10:11"):
            with self.subTest(time_range=time_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="09:10", end_time="10:11"),
                    source_text=(
                        "Add a dentist appointment on 2026-09-21 "
                        f"from {time_range} to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ())

    def test_explicit_time_syntax_disambiguates_dotted_endpoint(self) -> None:
        for time_range in ("09.10 bis 10:30", "09.10 to 10:30", "09.10-10.30 Uhr"):
            with self.subTest(time_range=time_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="09:10", end_time="10:30"),
                    source_text=(
                        "Add a dentist appointment on 2026-09-21 "
                        f"from {time_range} to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, ())

    def test_time_range_cannot_start_inside_a_spaced_date(self) -> None:
        for source_date, start_time, missing in (
            ("2026 - 09.21", "09:21", ("start_time",)),
            ("21 . 09.26", "09:26", ("date_with_year", "start_time")),
        ):
            with self.subTest(source_date=source_date):
                assessment = assess_calendar_create_draft(
                    _draft(start_time=start_time, end_time="10:00"),
                    source_text=(
                        f"Add a dentist appointment on {source_date} "
                        "to 10:00 to the family calendar."
                    ),
                )
                self.assertEqual(assessment.missing, missing)

    def test_range_endpoint_cannot_be_a_complete_date_prefix(self) -> None:
        for start, separator, year in product(
            ("09:00", "09.10"),
            (".", ". ", " /", " / ", " -", " - "),
            ("2026", "26"),
        ):
            source_range = f"{start} bis 10.11{separator}{year}"
            with self.subTest(source_range=source_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time=start.replace(".", ":"), end_time="10:11"),
                    source_text=(
                        "Zahnarzt am 21.09.2026 im Familienkalender "
                        f"von {source_range}."
                    ),
                )
                self.assertIn("end_time", assessment.missing)

    def test_range_start_cannot_be_a_complete_date_suffix(self) -> None:
        for prefix, separator in product(
            ("2026", "21"), (".", ". ", " /", " / ", " -", " - ")
        ):
            source_range = f"{prefix}{separator}09.21 bis 10:00"
            with self.subTest(source_range=source_range):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="09:21", end_time="10:00"),
                    source_text=(
                        "Zahnarzt am 21.09.2026 im Familienkalender "
                        f"von {source_range}."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time",))

    def test_meridiem_requests_require_explicit_24_hour_restatement(self) -> None:
        # Reject the whole request's time evidence, including shared suffixes
        # and mixtures: do not guess which endpoint an AM/PM marker modifies.
        for times in (
            "4:00 pm to 5:00 pm", "4:00 PM-5:00 PM", "4:00 p.m.-5:00 p.m.",
            "4:00-5:00 pm", "4.00–5.00 p. m.", "4:00pm to 5:00pm",
            "4:00 am to 5:00 am", "4:00 a.m.-5:00", "4 pm to 05:00",
            "04:00 to 05:00; another appointment at 4:00 pm",
        ):
            with self.subTest(times=times):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="04:00", end_time="05:00"),
                    source_text=(
                        "Dentist on 2026-09-21 in the family calendar "
                        f"from {times}."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time", "end_time"))

    def test_whole_hour_requires_a_separate_time_token(self) -> None:
        for source_time in ("A16 Uhr", "16:16 Uhr", "26.16 Uhr", "A16Uhr"):
            with self.subTest(source_time=source_time):
                assessment = assess_calendar_create_draft(
                    _draft(start_time="16:00", end_time="17:00"),
                    source_text=(
                        "Zahnarzt am 21.09.2026 im Familienkalender "
                        f"{source_time}, Ende 17:00."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time",))

    def test_german_date_preposition_after_24_hour_times_is_supported(self) -> None:
        for times in ("16:00 bis 16:30", "16.00-16.30", "16 Uhr-16:30 Uhr"):
            with self.subTest(times=times):
                assessment = assess_calendar_create_draft(
                    _draft(),
                    source_text=(
                        f"Zahnarzt von {times} am 21.09.2026 "
                        "im Familienkalender."
                    ),
                )
                self.assertEqual(assessment.missing, ())

    def test_explicit_24_hour_ranges_remain_supported(self) -> None:
        for hour, minute, separator, joiner in product(
            (0, 7, 9, 16, 22), (0, 10, 30, 59), (":", "."),
            (" - ", "–", " bis ", " to "),
        ):
            source_range = (
                f"{hour:02d}{separator}{minute:02d}{joiner}"
                f"{hour + 1:02d}{separator}{minute:02d} Uhr"
            )
            with self.subTest(source_range=source_range):
                assessment = assess_calendar_create_draft(
                    _draft(
                        start_time=f"{hour:02d}:{minute:02d}",
                        end_time=f"{hour + 1:02d}:{minute:02d}",
                    ),
                    source_text=(
                        "Zahnarzt am 21.09.2026 im Familienkalender "
                        f"von {source_range}."
                    ),
                )
                self.assertEqual(assessment.missing, ())

    def test_range_seconds_cannot_be_truncated_to_minutes(self) -> None:
        for source_range in (
            "16:00:30-16:30:45", "16.00.30-16.30.45",
            "16:00.30 bis 16:30.45", "16.00:30 to 16.30:45",
        ):
            with self.subTest(source_range=source_range):
                assessment = assess_calendar_create_draft(
                    _draft(),
                    source_text=(
                        "Dentist on 2026-09-21 in the family calendar "
                        f"from {source_range}."
                    ),
                )
                self.assertEqual(assessment.missing, ("start_time", "end_time"))

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

    def test_explicit_calendar_target_can_be_corroborated(self) -> None:
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

        self.assertEqual(assessment.missing, ())

    def test_mismatched_calendar_target_is_not_accepted(self) -> None:
        draft = _draft(
            calendar_id="family",
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
