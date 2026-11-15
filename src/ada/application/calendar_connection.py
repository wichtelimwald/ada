"""Trusted CalDAV pilot configuration and read-only connection probe (MVP-60 S6).

The file holds provider identifiers and references, never the app password.
It is read only by the operator-initiated CLI, not by the model or Memory.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef

_MAX_CONFIG_BYTES = 64 * 1024


class CalendarConnectionConfigurationError(ValueError):
    """Trusted CalDAV configuration is absent, unsafe or malformed."""


@dataclass(frozen=True, slots=True, repr=False)
class CalendarConnectionConfig:
    base_url: str
    username: str
    password_ref: str
    calendars: tuple[CalendarRef, ...]


def _required_string(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CalendarConnectionConfigurationError("invalid CalDAV configuration")
    if any(character in value for character in "\r\n\t\x00"):
        raise CalendarConnectionConfigurationError("invalid CalDAV configuration")
    return value


def load_connection_config(path: str | Path) -> CalendarConnectionConfig:
    """Read an owner-only regular JSON file, without following its final symlink."""

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as source:
            metadata = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_mode & 0o077
                or not 0 < metadata.st_size <= _MAX_CONFIG_BYTES
            ):
                raise CalendarConnectionConfigurationError(
                    "invalid CalDAV configuration"
                )
            raw = source.read(_MAX_CONFIG_BYTES + 1)
            if not 0 < len(raw) <= _MAX_CONFIG_BYTES:
                raise CalendarConnectionConfigurationError(
                    "invalid CalDAV configuration"
                )
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise CalendarConnectionConfigurationError(
            "invalid CalDAV configuration"
        ) from None

    if not isinstance(payload, dict) or set(payload) != {
        "provider", "base_url", "username", "password_ref", "calendars"
    } or payload["provider"] != "ionos":
        raise CalendarConnectionConfigurationError("invalid CalDAV configuration")

    base_url = _required_string(payload["base_url"])
    try:
        url = urlsplit(base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
        ):
            raise CalendarConnectionConfigurationError("invalid CalDAV origin")
        # Force malformed port values to fail before the password is unlocked.
        _ = url.port
    except ValueError:
        raise CalendarConnectionConfigurationError("invalid CalDAV origin") from None

    username = _required_string(payload["username"])
    if ":" in username:
        raise CalendarConnectionConfigurationError("invalid CalDAV configuration")
    password_ref = _required_string(payload["password_ref"])

    raw_calendars = payload["calendars"]
    if not isinstance(raw_calendars, list) or not 0 < len(raw_calendars) <= 12:
        raise CalendarConnectionConfigurationError("invalid CalDAV calendars")

    refs: list[CalendarRef] = []
    seen: set[str] = set()
    for item in raw_calendars:
        if not isinstance(item, dict) or set(item) != {
            "id", "collection", "audience", "mode"
        }:
            raise CalendarConnectionConfigurationError("invalid CalDAV calendars")
        calendar_id = _required_string(item["id"])
        collection = _required_string(item["collection"])
        if (
            calendar_id in seen
            or not collection.startswith("/")
            or collection.startswith("//")
            or any(char in collection for char in "?#\\")
        ):
            raise CalendarConnectionConfigurationError("invalid CalDAV calendars")
        seen.add(calendar_id)
        try:
            audience = CalendarAudience(item["audience"])
            mode = CalendarAccessMode(item["mode"])
        except (TypeError, ValueError):
            raise CalendarConnectionConfigurationError("invalid CalDAV calendars") from None
        refs.append(
            CalendarRef(
                calendar_id=calendar_id,
                provider_collection=collection,
                audience=audience,
                access_mode=mode,
            )
        )
    return CalendarConnectionConfig(
        base_url=base_url,
        username=username,
        password_ref=password_ref,
        calendars=tuple(refs),
    )


def probe_connection(
    config: CalendarConnectionConfig,
    password: str,
    *,
    transport: object = None,
    now: datetime | None = None,
) -> tuple[int, int]:
    """PROPFIND configured privileges, then REPORT seven days of events.

    Read-only: no calendar writes, no event titles/locations in the result,
    no DBOS persistence, and no model tool. The CLI only prints counts.
    """

    from ada.adapters.caldav import CalDAVCalendarAdapter, IONOS_PROFILE

    now = now if now is not None else datetime.now(timezone.utc)
    adapter = CalDAVCalendarAdapter(
        base_url=config.base_url,
        auth=(config.username, password),
        calendars=config.calendars,
        profile=IONOS_PROFILE,
        transport=transport,
        clock=lambda: now,
    )
    try:
        adapter.verify_configured_access()
        events = adapter.list_events(start=now, end=now + timedelta(days=7))
        return len(config.calendars), len(events)
    finally:
        adapter.close()
