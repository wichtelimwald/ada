from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone

import httpx2

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE, CalDAVProviderProfile
from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef
from caldav_fake_ionos_server import FakeIonosCalDAVServer

BASE_URL = "https://dav.mailbusiness.ionos.test"
FAKE_AUTH = ("ada-fake@example.test", "fake-app-password")

FAMILY_PATH = "/caldav/family-configured/"
FAMILY_CANONICAL_HREF = "/caldav/ZmFtaWx5LWNhbG9OMA/"

READ_ONLY_PATH = "/caldav/guardian-a-configured/"
READ_ONLY_CANONICAL_HREF = "/caldav/Z3VhcmRpYW4tYS1jYWwwMA/"


def default_family_ref() -> CalendarRef:
    return CalendarRef(
        calendar_id="family",
        provider_collection=FAMILY_PATH,
        audience=CalendarAudience.FAMILY,
        access_mode=CalendarAccessMode.WRITE,
    )


def default_read_only_ref() -> CalendarRef:
    return CalendarRef(
        calendar_id="guardian-a",
        provider_collection=READ_ONLY_PATH,
        audience=CalendarAudience.PERSON,
        access_mode=CalendarAccessMode.READ,
    )


def build_fake_server() -> FakeIonosCalDAVServer:
    server = FakeIonosCalDAVServer()
    server.add_collection(
        FAMILY_PATH,
        canonical_href=FAMILY_CANONICAL_HREF,
        privileges=frozenset({"read", "write"}),
    )
    server.add_collection(
        READ_ONLY_PATH,
        canonical_href=READ_ONLY_CANONICAL_HREF,
        privileges=frozenset({"read"}),
    )
    return server


def build_adapter(
    server: FakeIonosCalDAVServer,
    *,
    calendars: Sequence[CalendarRef] | None = None,
    profile: CalDAVProviderProfile = IONOS_PROFILE,
    clock: Callable[[], datetime] | None = None,
) -> CalDAVCalendarAdapter:
    return CalDAVCalendarAdapter(
        base_url=BASE_URL,
        auth=FAKE_AUTH,
        calendars=calendars or (default_family_ref(), default_read_only_ref()),
        profile=profile,
        transport=httpx2.MockTransport(server),
        clock=clock or (lambda: datetime(2026, 10, 1, tzinfo=timezone.utc)),
    )
