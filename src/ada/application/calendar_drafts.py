from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from ada.core.actions import CreateCalendarEventDraft


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_NUMERIC_DATE_RE = re.compile(
    r"(?<!\d)(?:\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}|"
    r"\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*(?:\d{4}|\d{2}))(?!\d)"
)
_SOURCE_TIME_TOKEN = r"(?:[01]?\d|2[0-3])[:.][0-5]\d"
_SOURCE_TIME_RANGE_RE = re.compile(
    rf"(?<![\w:./-])(?P<start>{_SOURCE_TIME_TOKEN})\s*"
    rf"(?:[-–—]|\b(?:to|bis)\b)\s*(?P<end>{_SOURCE_TIME_TOKEN})"
    # A range must not stop inside a date, including before a spaced year.
    r"(?![\w:]|\s*[./-]\s*\d)",
    re.IGNORECASE,
)
_MERIDIEM_TIME_RE = re.compile(
    # Only a 12-hour clock can carry a meridiem. In German, "16:30 am ..."
    # introduces a date; do not reinterpret its minutes as a separate hour.
    r"(?<![\w:.])(?:0?[1-9]|1[0-2])(?:[:.]\d{2})?\s*[ap]\.?\s*m\.?(?!\w)",
    re.IGNORECASE,
)
_DAY_PERIOD_TIME_RE = re.compile(
    # Day-period words make a 1-12 hour expression semantically 12-hour input.
    # Reject the request's time evidence rather than corroborating a different
    # 24-hour interpretation (for example, 4:00 nachmittags -> 04:00).
    r"(?<![\w:.])(?:0?[1-9]|1[0-2])(?:[:.]\d{2})?(?:\s+Uhr)?\s+"
    r"(?:morgens|vormittags|mittags|nachmittags|abends|nachts|früh|"
    r"in\s+the\s+(?:morning|afternoon|evening)|at\s+night)\b",
    re.IGNORECASE,
)
_MONTHS_DE = (
    "januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
    "september", "oktober", "november", "dezember",
)


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
    if any(re.search(pattern, source_text) for pattern in patterns):
        return True
    # A written month is equally explicit; require day, month and four-digit
    # year together so a year elsewhere in the message cannot corroborate it.
    month_name = _MONTHS_DE[value.month - 1]
    if month_name == "märz":
        month_name = r"(?:märz|maerz)"
    return bool(re.search(
        rf"(?<!\d)0?{day}\.?(?:\s+){month_name}\s+{year}(?!\d)",
        source_text, re.IGNORECASE,
    ))


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


def _could_be_day_first_partial_date(token: str) -> bool:
    if ":" in token:
        return False
    day, month = (int(part) for part in token.split("."))
    return 1 <= day <= 31 and 1 <= month <= 12


def _could_be_month_first_partial_date(token: str) -> bool:
    if ":" in token:
        return False
    month, day = (int(part) for part in token.split("."))
    return 1 <= month <= 12 and 1 <= day <= 31


def _could_be_partial_date(token: str) -> bool:
    return (
        _could_be_day_first_partial_date(token)
        or _could_be_month_first_partial_date(token)
    )


def _source_explicitly_supports_time(value: str, source_text: str) -> bool:
    # This slice accepts 24-hour input only. Reject 12-hour/meridiem or
    # day-period requests as a whole rather than guessing suffix scope.
    if (
        _MERIDIEM_TIME_RE.search(source_text)
        or _DAY_PERIOD_TIME_RE.search(source_text)
    ):
        return False
    hour, minute = (int(part) for part in value.strip().split(":"))
    date_spans = [match.span() for match in _NUMERIC_DATE_RE.finditer(source_text)]

    def normalize_range(match: re.Match[str]) -> str:
        if any(
            start < match.start() < end or start < match.end() < end
            for start, end in date_spans
        ):
            # Check both original boundaries before changing any dots: neither
            # a date suffix nor a date prefix can become time evidence.
            return match.group(0)
        start, end = match.group("start", "end")
        if _could_be_partial_date(start) and re.search(
            r"\b(?:am|on|den)\s*$", source_text[:match.start()], re.IGNORECASE
        ):
            return match.group(0)
        has_time_marker = re.match(r"\s+Uhr\b", source_text[match.end():], re.IGNORECASE)
        same_date_order = (
            (
                _could_be_day_first_partial_date(start)
                and _could_be_day_first_partial_date(end)
            )
            or (
                _could_be_month_first_partial_date(start)
                and _could_be_month_first_partial_date(end)
            )
        )
        if same_date_order and not has_time_marker:
            # A fully dotted range is ambiguous when both endpoints form
            # valid partial dates in the same ordering (DD.MM or MM.DD).
            # Require explicit time syntax instead of guessing.
            return " "
        # Protect an explicit time range before masking three-part dates;
        # otherwise 16.30-17.00 is partly consumed as a date token.
        return f"{start.replace('.', ':')} - {end.replace('.', ':')}"

    time_ranges_normalized = _SOURCE_TIME_RANGE_RE.sub(normalize_range, source_text)
    # A complete numeric date may contain a dotted month/day fragment that
    # resembles a time, including when the date uses mixed separators.
    # Two-digit years are masked too, without using them to infer a century.
    without_dates = _NUMERIC_DATE_RE.sub(" ", time_ranges_normalized)
    forms = [rf"(?<![\w:.])0?{hour}:{minute:02d}(?![\w:]|\.\d)"]
    dotted = rf"(?<![\w:./-])0?{hour}\.{minute:02d}"
    if _could_be_partial_date(f"{hour}.{minute:02d}"):
        # 21.09 or 21.09. alone is not evidence for 21:09.
        dotted += r"\s+Uhr\b"
    else:
        dotted += r"(?![\w:]|\.\d)"
    forms.append(dotted)
    if minute == 0:
        forms.append(
            rf"(?<![\w:./])0?{hour}\s+Uhr(?!\w)(?!\s+\d{{1,2}}\b)"
        )
    return any(re.search(form, without_dates, re.IGNORECASE) for form in forms)


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

    if not start_valid or not _source_explicitly_supports_time(
        draft.start_time or "", source_text
    ):
        missing.append("start_time")
    if not end_valid or not _source_explicitly_supports_time(
        draft.end_time or "", source_text
    ):
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
    "end_time": "gültige Endzeit",
    "calendar": "Zielkalender",
    "calendar_id": "Zielkalender",
}

_EN_LABELS = {
    "title": "title/purpose",
    "date_with_year": "full valid date including year",
    "year": "year",
    "date": "date",
    "start_time": "start time",
    "end_time": "valid end time",
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
            f"Mir fehlt noch: {joined}. "
            "Bitte sende den vollständigen Termin mit Titel, Datum mit Jahr, "
            "Start- und Endzeit (24-Stunden-Format HH:MM) sowie Zielkalender "
            "in einer Nachricht."
        )
    return (
        "I have not changed the calendar. "
        f"I still need: {joined}. "
        "Please send the complete event with title, date including year, "
        "start and end times (24-hour HH:MM), and target calendar in one message."
    )
