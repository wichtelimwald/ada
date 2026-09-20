from __future__ import annotations

from dataclasses import dataclass
import re

from ada.core.actions import CreateCalendarEventDraft


_FULL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True, slots=True)
class CalendarDraftAssessment:
    """Deterministic assessment of a non-executable calendar draft."""

    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing


def assess_calendar_create_draft(
    draft: CreateCalendarEventDraft,
) -> CalendarDraftAssessment:
    """Identify material information still required before proposal creation."""

    missing: list[str] = []

    if not draft.title or not draft.title.strip():
        missing.append("title")

    if not draft.date or not _FULL_DATE_RE.fullmatch(draft.date.strip()):
        missing.append("date_with_year")

    if (
        not draft.start_time
        or not _TIME_RE.fullmatch(draft.start_time.strip())
    ):
        missing.append("start_time")

    if (
        not draft.end_time
        or not _TIME_RE.fullmatch(draft.end_time.strip())
    ):
        missing.append("end_time")

    if not draft.calendar_id or not draft.calendar_id.strip():
        missing.append("calendar")

    for item in draft.unresolved:
        normalized = item.strip().lower()
        if normalized and normalized not in missing:
            missing.append(normalized)

    return CalendarDraftAssessment(missing=tuple(missing))


_DE_LABELS = {
    "title": "Titel/Anlass",
    "date_with_year": "vollständiges Datum mit Jahr",
    "year": "Jahr",
    "date": "Datum",
    "start_time": "Startzeit",
    "end_time": "Endzeit oder Dauer",
    "calendar": "Zielkalender",
    "calendar_id": "Zielkalender",
}

_EN_LABELS = {
    "title": "title/purpose",
    "date_with_year": "full date including year",
    "year": "year",
    "date": "date",
    "start_time": "start time",
    "end_time": "end time or duration",
    "calendar": "target calendar",
    "calendar_id": "target calendar",
}


def render_calendar_draft_response(
    draft: CreateCalendarEventDraft,
) -> str:
    """Render a safe user-facing result without implying external execution."""

    assessment = assess_calendar_create_draft(draft)
    german = draft.language == "de"

    if assessment.complete:
        if german:
            return (
                "Ich habe den Termin als Entwurf verstanden, aber noch nichts "
                "in den Kalender eingetragen."
            )
        return (
            "I understood the calendar request as a draft, but I have not "
            "changed the calendar."
        )

    labels = _DE_LABELS if german else _EN_LABELS
    missing = [labels.get(item, item) for item in assessment.missing]

    if len(missing) == 1:
        joined = missing[0]
    else:
        joined = ", ".join(missing[:-1])
        joined += (" und " if german else " and ") + missing[-1]

    if german:
        return (
            "Ich habe noch nichts in den Kalender eingetragen. "
            f"Mir fehlt noch: {joined}."
        )
    return (
        "I have not changed the calendar. "
        f"I still need: {joined}."
    )
