from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib

import icalendar

import recurring_ical_events

from ada.core.actions import (
    CreateCalendarEventProposal,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import CalendarEvent


OPERATION_MARKER_PROPERTY = "X-ADA-OPERATION-MARKER"

_FREQ_SECONDS = {
    "SECONDLY": 1,
    "MINUTELY": 60,
    "HOURLY": 3600,
    "DAILY": 86400,
    "WEEKLY": 7 * 86400,
    # Conservative lower bounds: real month/year lengths vary, and a bound
    # that is too small (never too large) is the safe direction for a budget.
    "MONTHLY": 28 * 86400,
    "YEARLY": 365 * 86400,
}


class CalDAVMappingError(RuntimeError):
    """A CalDAV resource did not have the shape Ada's mapping expects."""


class FloatingTimeNotSupportedError(CalDAVMappingError):
    """A floating (timezone-unspecified) DATE-TIME was rejected.

    RFC 5545 S3.3.5: a DATE-TIME without ``Z`` and without ``TZID`` is
    floating, explicitly *not* bound to UTC. Ada has no configured
    calendar/user timezone yet (a later decision); guessing UTC would
    silently shift busy/conflict intervals, so this fails closed instead.
    """


class WriteScopeError(CalDAVMappingError):
    """The resource is outside Ada's MVP write scope (ADR-0009 section 6).

    Recurring series, single occurrences and events with attendees are
    read-only for Ada and fail closed before any write is sent.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CalendarComplexityExceededError(RuntimeError):
    """Untrusted calendar data exceeded a deterministic complexity limit.

    ADR-0009 section 5: exceeding a limit fails closed for the affected
    calendar with a user-visible explanation, and must never depend on a
    provider's current recurrence support.
    """


def _first(value: object) -> object:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _rdate_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, list):
        return sum(_rdate_count(item) for item in value)
    try:
        return len(value)  # type: ignore[arg-type]
    except TypeError:
        return 1


def _property_count(component: "icalendar.cal.Component") -> int:
    total = 0
    for value in component.values():
        total += len(value) if isinstance(value, list) else 1
    return total


# RFC 5545 S3.3.10: BYSECOND/BYMINUTE/BYHOUR can only ever narrow the time
# between generated occurrences down to their named granularity; the
# date-level parts (BYDAY, BYMONTHDAY, BYYEARDAY, BYWEEKNO, BYMONTH) can
# narrow it down to one day (they can never produce two occurrences on the
# same calendar day). BYSETPOS only *selects from* an already-generated set,
# so it can only reduce a count, never increase one, and is intentionally
# excluded below.
_SUB_DAY_GRANULARITY_SECONDS = {
    "BYSECOND": 1,
    "BYMINUTE": 60,
    "BYHOUR": 3600,
}
_DATE_LEVEL_PARTS = ("BYDAY", "BYMONTHDAY", "BYYEARDAY", "BYWEEKNO", "BYMONTH")


def _rrule_granularity_seconds(
    rrule: "icalendar.prop.recur.recur.vRecur", base_period_seconds: int
) -> int:
    """A safe (never too large) floor on the spacing between occurrences.

    This does not attempt to model RFC 5545's exact BYxxx combinatorics
    (BYMONTH + BYDAY interactions, BYSETPOS selection, leap units, ...);
    doing that precisely is its own source of bugs. Instead it asks only
    "what is the finest granularity any present BYxxx part could possibly
    introduce", which is always a valid (if sometimes pessimistic) upper
    bound on how many occurrences can appear in a given time span, however
    the present BYxxx parts combine.
    """

    granularity = base_period_seconds
    for name, seconds in _SUB_DAY_GRANULARITY_SECONDS.items():
        if rrule.get(name) is not None:
            granularity = min(granularity, seconds)
    if any(rrule.get(name) is not None for name in _DATE_LEVEL_PARTS):
        granularity = min(granularity, 86400)
    return max(granularity, 1)


def estimate_series_occurrence_bound(
    component: "icalendar.cal.Component",
    *,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Cheap analytical upper bound on occurrences within the window.

    Computed from RRULE/RDATE alone, without expanding anything, so a
    pathological pattern (for example ``FREQ=SECONDLY``, or ``FREQ=DAILY``
    combined with many ``BYHOUR``/``BYMINUTE`` values, over a wide window)
    is rejected before any real expansion runs ("expanded lazily against
    that budget", ADR-0009 section 5). An unrecognized/malformed ``FREQ``
    is treated as the worst case rather than ignored.
    """

    bound = 1  # the master's own DTSTART occurrence

    rrule = component.get("rrule")
    if rrule is not None:
        freq = str(_first(rrule.get("FREQ")) or "").upper()
        interval_raw = _first(rrule.get("INTERVAL"))
        try:
            interval = int(interval_raw) if interval_raw is not None else 1
        except (TypeError, ValueError):
            interval = 1
        if interval <= 0:
            interval = 1

        base_period_seconds = _FREQ_SECONDS.get(freq, 1) * interval
        granularity_seconds = _rrule_granularity_seconds(rrule, base_period_seconds)
        window_seconds = max((window_end - window_start).total_seconds(), 0.0)
        by_window = int(window_seconds // granularity_seconds) + 1

        count_raw = _first(rrule.get("COUNT"))
        try:
            count = int(count_raw) if count_raw is not None else None
        except (TypeError, ValueError):
            count = None

        bound += min(count, by_window) if count is not None else by_window

    bound += _rdate_count(component.get("rdate"))
    return bound


def _is_all_day(value: object) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _as_utc_datetime(value: "date | datetime") -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise FloatingTimeNotSupportedError(
                "floating (timezone-unspecified) DATE-TIME is not supported"
            )
        return value.astimezone(timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _resolve_end(
    dtstart: "date | datetime", dtend_prop: object, duration_prop: object = None
) -> "date | datetime":
    """The event's end value, applying RFC 5545's implicit-duration defaults.

    A ``DTEND``/``DURATION`` takes priority when present. Otherwise: a
    ``DATE``-only ``DTSTART`` (an all-day event) has an implicit one-day
    duration (RFC 5545 S3.6.1) — using ``dtstart`` itself would silently
    make the event zero-length and drop it from boundary overlap checks. A
    ``DATE-TIME`` ``DTSTART`` without either has no RFC-defined default;
    Ada keeps the existing zero-length fallback for that case.
    """

    if dtend_prop is not None:
        return dtend_prop.dt  # type: ignore[attr-defined]
    if duration_prop is not None:
        return dtstart + duration_prop.dt  # type: ignore[attr-defined]
    if isinstance(dtstart, datetime):
        return dtstart
    return dtstart + timedelta(days=1)


def _is_busy(component: "icalendar.cal.Component") -> bool:
    transp = str(component.get("transp", "OPAQUE") or "OPAQUE").upper()
    status = str(component.get("status", "") or "").upper()
    if status == "CANCELLED":
        return False
    return transp != "TRANSPARENT"


def _has_attendees(component: "icalendar.cal.Component") -> bool:
    return component.get("attendee") is not None


def _sequence(component: "icalendar.cal.Component") -> int:
    raw = component.get("sequence")
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def component_sequence(component: "icalendar.cal.Component") -> int:
    return _sequence(component)


def _text_or_none(component: "icalendar.cal.Component", name: str) -> str | None:
    value = component.get(name)
    return str(value) if value else None


@dataclass(frozen=True, slots=True)
class MappedResource:
    """One CalDAV resource's mapped occurrences plus its raw component count."""

    events: tuple[CalendarEvent, ...]
    component_count: int


def map_resource_occurrences(
    *,
    calendar_id: str,
    resource_name: str,
    calendar_data: bytes,
    version: EventVersion | None,
    window_start: datetime,
    window_end: datetime,
    max_properties_per_component: int,
    max_occurrences_per_series: int,
    remaining_component_budget: int,
    remaining_occurrence_budget: int,
) -> MappedResource:
    """Parse one CalDAV resource's iCalendar data into Ada's read model.

    Expands recurrences client-side (decision D1, ``recurring-ical-events``)
    because OX/IONOS does not do so server-side (evaluation section 3).

    ``remaining_component_budget``/``remaining_occurrence_budget`` are the
    caller's per-response/per-query budgets *still available* before this
    resource. Both are checked, using only cheap pre-expansion facts (raw
    component count; the analytical per-series bound), before
    ``recurring_ical_events`` is ever invoked: a resource containing several
    individually-small recurring masters must not be allowed to expand past
    the query's total budget just because each master passes its own
    per-series check (ADR-0009 section 5: "expanded lazily against that
    budget").
    """

    calendar = icalendar.Calendar.from_ical(calendar_data)
    all_vevents = list(calendar.walk("VEVENT"))

    if len(all_vevents) > remaining_component_budget:
        raise CalendarComplexityExceededError(
            f"event resource {resource_name!r} exceeds the remaining "
            "per-response component budget"
        )

    for component in all_vevents:
        if _property_count(component) > max_properties_per_component:
            raise CalendarComplexityExceededError(
                f"event resource {resource_name!r} exceeds the per-component "
                "property limit"
            )

    masters = [c for c in all_vevents if c.get("recurrence-id") is None]
    if not masters:
        return MappedResource(events=(), component_count=len(all_vevents))

    recurring_by_uid = {
        str(master.get("uid")): (
            master.get("rrule") is not None or master.get("rdate") is not None
        )
        for master in masters
    }

    per_master_bounds: list[int] = []
    for master in masters:
        bound = estimate_series_occurrence_bound(
            master, window_start=window_start, window_end=window_end
        )
        if bound > max_occurrences_per_series:
            raise CalendarComplexityExceededError(
                f"event resource {resource_name!r} series "
                f"{master.get('uid')!r} exceeds the per-series occurrence "
                f"budget ({bound} > {max_occurrences_per_series})"
            )
        per_master_bounds.append(bound)

    if sum(per_master_bounds) > remaining_occurrence_budget:
        raise CalendarComplexityExceededError(
            f"event resource {resource_name!r} exceeds the remaining "
            "per-query occurrence budget before any expansion ran"
        )

    occurrences = recurring_ical_events.of(calendar).between(
        window_start, window_end
    )

    if len(occurrences) > remaining_occurrence_budget:
        # Defense in depth only: the pre-expansion bound above is meant to
        # always be conservative enough that this never triggers. Trusting
        # that blindly would defeat the point of a security budget.
        raise CalendarComplexityExceededError(
            f"event resource {resource_name!r} produced more occurrences "
            "than its own pre-expansion bound predicted"
        )

    events: list[CalendarEvent] = []
    for occurrence in occurrences:
        dtstart_prop = occurrence.get("dtstart")
        if dtstart_prop is None:
            raise CalDAVMappingError(
                f"event resource {resource_name!r} has an occurrence without DTSTART"
            )
        dtstart = dtstart_prop.dt

        dtend = _resolve_end(
            dtstart, occurrence.get("dtend"), occurrence.get("duration")
        )

        uid = str(occurrence.get("uid"))
        is_recurring = recurring_by_uid.get(uid, False)

        if is_recurring:
            # One resource now yields several occurrences; they need distinct
            # ids. A plain, non-recurring resource keeps the same event_id as
            # the create/read-back path (map_single_event), which addresses
            # it by resource_name alone.
            recurrence_id = occurrence.get("recurrence-id")
            occurrence_key = (
                _as_utc_datetime(recurrence_id.dt).isoformat()
                if recurrence_id is not None
                else _as_utc_datetime(dtstart).isoformat()
            )
            event_id = f"{resource_name}#{occurrence_key}"
        else:
            event_id = resource_name

        events.append(
            CalendarEvent(
                event_id=event_id,
                title=str(occurrence.get("summary", "") or ""),
                start=_as_utc_datetime(dtstart),
                end=_as_utc_datetime(dtend),
                calendar_id=calendar_id,
                location=_text_or_none(occurrence, "location"),
                event_ref=EventRef(
                    calendar_id=calendar_id, resource_name=resource_name
                ),
                version=version,
                busy=_is_busy(occurrence),
                all_day=_is_all_day(dtstart),
                recurring=is_recurring,
                has_attendees=_has_attendees(occurrence),
                sequence=_sequence(occurrence),
            )
        )

    return MappedResource(events=tuple(events), component_count=len(all_vevents))


def parse_single_vevent(
    calendar_data: bytes, *, resource_name: str
) -> "icalendar.cal.Component":
    """Parse a resource Ada expects to hold exactly one non-recurring VEVENT.

    Used only for Ada's own created/read-back events (MVP write scope is
    non-recurring and attendee-less; ADR-0009 section 6), never for
    arbitrary provider data, so no complexity budget is applied here.
    """

    calendar = icalendar.Calendar.from_ical(calendar_data)
    vevents = list(calendar.walk("VEVENT"))
    if len(vevents) != 1:
        raise CalDAVMappingError(
            f"expected exactly one VEVENT in {resource_name!r}, "
            f"found {len(vevents)}"
        )
    return vevents[0]


def component_operation_marker(component: "icalendar.cal.Component") -> str | None:
    marker = component.get(OPERATION_MARKER_PROPERTY)
    return str(marker) if marker is not None else None


def build_calendar_event_from_component(
    component: "icalendar.cal.Component",
    *,
    calendar_id: str,
    resource_name: str,
    version: EventVersion | None,
) -> CalendarEvent:
    dtstart_prop = component.get("dtstart")
    if dtstart_prop is None:
        raise CalDAVMappingError(
            f"event resource {resource_name!r} is missing DTSTART"
        )
    dtstart = dtstart_prop.dt

    dtend = _resolve_end(dtstart, component.get("dtend"), component.get("duration"))

    return CalendarEvent(
        event_id=resource_name,
        title=str(component.get("summary", "") or ""),
        start=_as_utc_datetime(dtstart),
        end=_as_utc_datetime(dtend),
        calendar_id=calendar_id,
        location=_text_or_none(component, "location"),
        event_ref=EventRef(calendar_id=calendar_id, resource_name=resource_name),
        version=version,
        busy=_is_busy(component),
        all_day=_is_all_day(dtstart),
        recurring=component.get("rrule") is not None
        or component.get("rdate") is not None,
        has_attendees=_has_attendees(component),
        sequence=_sequence(component),
    )


def map_single_event(
    *,
    calendar_id: str,
    resource_name: str,
    calendar_data: bytes,
    version: EventVersion | None,
) -> CalendarEvent:
    component = parse_single_vevent(calendar_data, resource_name=resource_name)
    return build_calendar_event_from_component(
        component,
        calendar_id=calendar_id,
        resource_name=resource_name,
        version=version,
    )


def _operation_digest(operation_id: str) -> str:
    return hashlib.sha256(operation_id.encode("utf-8")).hexdigest()


def derive_event_uid(operation_id: str) -> str:
    """A deterministic, non-semantic UID stable across retries of the same op."""

    return f"ada-{_operation_digest(operation_id)}@ada.local"


def derive_resource_name(operation_id: str) -> str:
    """A deterministic, non-semantic resource name stable across retries."""

    return f"ada-{_operation_digest(operation_id)}.ics"


def derive_operation_marker(operation_id: str) -> str:
    """Non-semantic reconciliation evidence; a hint, never authority."""

    return _operation_digest(operation_id)


def build_create_ical(
    proposal: CreateCalendarEventProposal,
    *,
    uid: str,
    marker: str,
) -> bytes:
    """Serialize Ada's create proposal as one attendee-less, non-recurring VEVENT.

    MVP write scope never emits RRULE or ATTENDEE (ADR-0009 section 6).
    """

    calendar = icalendar.Calendar()
    calendar.add("prodid", "-//Ada//CalDAV adapter//EN")
    calendar.add("version", "2.0")

    event = icalendar.Event()
    event.add("uid", uid)
    event.add("summary", proposal.title)
    event.add("dtstart", proposal.start.astimezone(timezone.utc))
    event.add("dtend", proposal.end.astimezone(timezone.utc))
    event.add("dtstamp", datetime.now(timezone.utc))
    event.add("sequence", 0)
    if proposal.location:
        event.add("location", proposal.location)
    event.add(OPERATION_MARKER_PROPERTY, marker)

    calendar.add_component(event)
    return calendar.to_ical()


def parse_calendar(calendar_data: bytes) -> "icalendar.Calendar":
    """Parse provider iCalendar data; malformed input is a typed mapping error
    rather than a raw parser exception."""

    try:
        return icalendar.Calendar.from_ical(calendar_data)
    except ValueError as exc:
        raise CalDAVMappingError(f"malformed iCalendar data: {exc}") from exc


def operation_marker_component(
    calendar: "icalendar.Calendar", marker: str
) -> "icalendar.cal.Component | None":
    """The VEVENT carrying ``marker``, whatever shape the resource has now.

    The marker is reconciliation evidence of an earlier write. Whether Ada may
    *write* the resource today (``writable_vevent``) is a separate question
    that only matters before a new write; a later edit that moved the event
    out of the write scope does not undo the earlier write.
    """

    for component in calendar.walk("VEVENT"):
        if component_operation_marker(component) == marker:
            return component
    return None


def writable_vevent(
    calendar: "icalendar.Calendar", resource_name: str
) -> "icalendar.cal.Component":
    """The single VEVENT Ada may update or cancel, or a refusal (fail closed).

    Only consulted when a new write may still be attempted.
    """

    vevents = list(calendar.walk("VEVENT"))
    if len(vevents) != 1:
        # Several VEVENTs mean a recurrence series with overrides.
        raise WriteScopeError(
            "recurring_event_read_only",
            f"{resource_name!r} holds {len(vevents)} VEVENT components",
        )
    component = vevents[0]
    if any(
        component.get(name) is not None
        for name in ("rrule", "rdate", "exdate", "recurrence-id")
    ):
        raise WriteScopeError(
            "recurring_event_read_only", f"{resource_name!r} is recurring"
        )
    if _has_attendees(component):
        raise WriteScopeError(
            "attendee_event_read_only", f"{resource_name!r} has attendees"
        )
    return component


def _replace(component: "icalendar.cal.Component", name: str, value: object) -> None:
    if name in component:
        del component[name]
    component.add(name, value)


def build_update_ical(
    calendar_data: bytes,
    proposal: UpdateCalendarEventProposal,
    *,
    marker: str,
) -> bytes:
    """Serialize an update as the existing VEVENT plus the requested changes.

    Every other property is carried over unchanged. The base ``SEQUENCE`` is
    incremented, ``DTSTAMP`` is fresh and the operation marker replaces any
    earlier one (ADR-0009 section 6). The result is deterministic apart from
    ``DTSTAMP``, so a replay writes the same ``SEQUENCE`` and marker.
    """

    resource_name = proposal.event_ref.resource_name
    calendar = parse_calendar(calendar_data)
    component = writable_vevent(calendar, resource_name)
    changes = proposal.changes

    if changes.start is not None or changes.end is not None:
        dtstart_prop = component.get("dtstart")
        if dtstart_prop is None:
            raise CalDAVMappingError(f"{resource_name!r} is missing DTSTART")
        if _is_all_day(dtstart_prop.dt):
            raise WriteScopeError(
                "all_day_time_change_unsupported",
                f"{resource_name!r} is an all-day event",
            )
        old_start = _as_utc_datetime(dtstart_prop.dt)
        old_end = _as_utc_datetime(
            _resolve_end(dtstart_prop.dt, component.get("dtend"), component.get("duration"))
        )
        new_start = (
            changes.start.astimezone(timezone.utc)
            if changes.start is not None
            else old_start
        )
        if changes.end is not None:
            new_end = changes.end.astimezone(timezone.utc)
        else:
            new_end = new_start + (old_end - old_start)
        if new_end <= new_start:
            raise WriteScopeError(
                "invalid_time_range", "the changed end is not after the start"
            )
        if "duration" in component:
            del component["duration"]
        _replace(component, "dtstart", new_start)
        _replace(component, "dtend", new_end)

    if changes.title is not None:
        _replace(component, "summary", changes.title)
    if changes.location is not None:
        _replace(component, "location", changes.location)

    _replace(component, "sequence", proposal.base_version.sequence + 1)
    _replace(component, "dtstamp", datetime.now(timezone.utc))
    _replace(component, OPERATION_MARKER_PROPERTY, marker)
    return calendar.to_ical()
