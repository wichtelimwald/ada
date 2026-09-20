from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from ada.core.actions import CreateCalendarEventDraft


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True, slots=True)
class CalendarDraftAssessment:
    """Deterministic assessment of a non-executable calendar draft."""

    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    normalized = value.strip()
    if not _ISO_DATE_RE.fullmatch(normalized):
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _source_explicitly_supports_date(
    value: date,
    source_text: str,
) -> bool:
    """Require the model's full date to be explicitly present in the user text.

    Be conservative: only recognize common complete numeric date forms where
    day/month/year occur together. A year-shaped room number or price elsewhere
    in the request must not validate a model-invented year.
    """

    year = str(value.year)
    month = str(value.month)
    day = str(value.day)

    patterns = (
        rf"(?<!\d){year}\s*[-/.]\s*0?{month}\s*[-/.]\s*0?{day}(?!\d)",
        rf"(?<!\d)0?{day}\s*[-/.]\s*0?{month}\s*[-/.]\s*{year}(?!\d)",
    )
    return any(re.search(pattern, source_text) for pattern in patterns)


def _source_explicitly_supports_calendar(
    calendar_id: str,
    source_text: str,
) -> bool:
    """Require the model's calendar target to be explicit in the user text."""

    normalized = " ".join(calendar_id.strip().lower().split())
    if not normalized:
        return False

    aliases = {normalized}
    if normalized == "family":
        aliases.update({"familie", "familien", "family"})

    for alias in aliases:
        escaped = re.escape(alias)
        patterns = (
            rf"(?<!\w){escaped}\s+calendar(?!\w)",
            rf"(?<!\w)calendar\s+{escaped}(?!\w)",
            rf"(?<!\w){escaped}\s*kalender(?!\w)",
            rf"(?<!\w)kalender\s+{escaped}(?!\w)",
        )
        if any(re.search(pattern, source_text, re.IGNORECASE) for pattern in patterns):
            return True
    return False


def _valid_time(value: str | None) -> bool:
    return bool(value and _TIME_RE.fullmatch(value.strip()))


def assess_calendar_create_draft(
    draft: CreateCalendarEventDraft,
    *,
    source_text: str,
) -> CalendarDraftAssessment:
    """Identify material information still required before proposal creation."""

    missing: list[str] = []

    if not draft.title or not draft.title.strip():
        missing.append("title")

    parsed_date = _parse_iso_date(draft.date)
    if parsed_date is None:
        missing.append("date_with_year")
    elif not _source_explicitly_supports_date(
        parsed_date,
        source_text,
    ):
        # The model must not silently invent or substitute a year/date.
        missing.append("date_with_year")

    start_valid = _valid_time(draft.start_time)
    end_valid = _valid_time(draft.end_time)

    if not start_valid:
        missing.append("start_time")
    if not end_valid:
        missing.append("end_time")
    elif start_valid:
        assert draft.start_time is not None
        assert draft.end_time is not None
        if draft.end_time.strip() <= draft.start_time.strip():
            # Drafts currently describe one calendar date, so an end time that
            # is not later than the start cannot be treated as complete.
            missing.append("end_time")

    if (
        not draft.calendar_id
        or not draft.calendar_id.strip()
        or not _source_explicitly_supports_calendar(
            draft.calendar_id,
            source_text,
        )
    ):
        missing.append("calendar")

    # Model-generated unresolved metadata is advisory only. Ada owns the
    # required-field policy and accepts only the small canonical set below.
    unresolved_aliases = {
        "year": "date_with_year",
        "date": "date_with_year",
        "duration": "end_time",
        "calendar_id": "calendar",
    }
    allowed_unresolved = {
        "title",
        "date_with_year",
        "start_time",
        "end_time",
        "calendar",
    }
    for item in draft.unresolved:
        normalized = item.strip().lower()
        normalized = unresolved_aliases.get(normalized, normalized)
        if normalized in allowed_unresolved and normalized not in missing:
            missing.append(normalized)

    return CalendarDraftAssessment(missing=tuple(missing))


_DE_LABELS = {
    "title": "Titel/Anlass",
    "date_with_year": "vollständiges und gültiges Datum mit Jahr",
    "year": "Jahr",
    "date": "Datum",
    "start_time": "Startzeit",
    "end_time": "gültige Endzeit oder Dauer",
    "calendar": "Zielkalender",
    "calendar_id": "Zielkalender",
}

_EN_LABELS = {
    "title": "title/purpose",
    "date_with_year": "full valid date including year",
    "year": "year",
    "date": "date",
    "start_time": "start time",
    "end_time": "valid end time or duration",
    "calendar": "target calendar",
    "calendar_id": "target calendar",
}


def render_calendar_draft_response(
    draft: CreateCalendarEventDraft,
    *,
    source_text: str,
) -> str:
    """Render a safe user-facing result without implying external execution."""

    assessment = assess_calendar_create_draft(
        draft,
        source_text=source_text,
    )
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
