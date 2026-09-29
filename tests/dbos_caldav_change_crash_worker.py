from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

import httpx2
from dbos import DBOS, DBOSConfig

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.core.action_outcomes import AuthorizationEvidence, OperationId
from ada.core.actions import (
    CalendarEventChanges,
    CancelCalendarEventProposal,
    EventBaseVersion,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef
from ada.ports.durable_action import DurableCalendarCancel, DurableCalendarUpdate

BASE_URL = "https://dav.mailbusiness.ionos.test"
COLLECTION_PATH = "/caldav/family/"
RESOURCE_NAME = "seeded-event.ics"
RESOURCE_PATH = f"{COLLECTION_PATH}{RESOURCE_NAME}"
SEED_ETAG = "e1"

SEED_BODY = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n"
    "BEGIN:VEVENT\r\nUID:seeded-uid@example.test\r\nDTSTAMP:20260901T000000Z\r\n"
    "DTSTART:20261012T160000Z\r\nDTEND:20261012T163000Z\r\n"
    "SUMMARY:Synthetic original title\r\nSEQUENCE:0\r\n"
    "END:VEVENT\r\nEND:VCALENDAR\r\n"
).encode("utf-8")


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS resources ("
        "path TEXT PRIMARY KEY, body BLOB NOT NULL, etag TEXT NOT NULL)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS calls ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL)"
    )
    con.commit()
    return con


class _PersistentFakeCalDAVServer:
    """Process-persistent fake CalDAV server for update/cancel crash tests.

    Speaks just enough CalDAV for ``CalDAVCalendarAdapter``'s update/cancel
    path: PROPFIND, GET with a stored ETag, and ``If-Match``-conditional PUT
    and DELETE. It hard-kills the process right after a write committed.
    """

    def __init__(self, provider_db: Path, *, crash_after_commit: bool) -> None:
        self._provider_db = provider_db
        self._crash_after_commit = crash_after_commit
        with closing(_connect(provider_db)):
            pass

    def _record(self, con: sqlite3.Connection, kind: str) -> None:
        con.execute("INSERT INTO calls(kind) VALUES (?)", (kind,))

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        method = request.method
        path = request.url.path

        if method == "PROPFIND":
            body = (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<D:multistatus xmlns:D="DAV:" xmlns:CS="http://calendarserver.org/ns/">'
                "<D:response>"
                f"<D:href>{COLLECTION_PATH}</D:href>"
                "<D:propstat><D:prop>"
                "<D:resourcetype><D:collection/></D:resourcetype>"
                "<D:current-user-privilege-set>"
                "<D:privilege><D:read/></D:privilege>"
                "<D:privilege><D:write/></D:privilege>"
                "</D:current-user-privilege-set>"
                "<CS:getctag>ctag-1</CS:getctag>"
                "</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat>"
                "</D:response></D:multistatus>"
            ).encode("utf-8")
            return httpx2.Response(
                207, content=body, headers={"Content-Type": "application/xml"}
            )

        with closing(_connect(self._provider_db)) as con:
            if method == "GET":
                self._record(con, "get")
                row = con.execute(
                    "SELECT body, etag FROM resources WHERE path = ?", (path,)
                ).fetchone()
                con.commit()
                if row is None:
                    return httpx2.Response(404, content=b"not found")
                return httpx2.Response(
                    200,
                    content=row[0],
                    headers={"Content-Type": "text/calendar", "ETag": f'"{row[1]}"'},
                )

            if method in ("PUT", "DELETE"):
                self._record(con, method.lower())
                row = con.execute(
                    "SELECT etag FROM resources WHERE path = ?", (path,)
                ).fetchone()
                if row is None:
                    con.commit()
                    return httpx2.Response(404, content=b"not found")
                if request.headers.get("if-match") != f'"{row[0]}"':
                    con.commit()
                    return httpx2.Response(412, content=b"precondition failed")
                if method == "PUT":
                    new_etag = f"e{int(row[0][1:]) + 1}"
                    con.execute(
                        "UPDATE resources SET body = ?, etag = ? WHERE path = ?",
                        (request.content, new_etag, path),
                    )
                else:
                    con.execute("DELETE FROM resources WHERE path = ?", (path,))
                con.commit()

                # Hard process death after the provider commit but before the
                # DBOS step wrapper can checkpoint the returned result.
                if self._crash_after_commit:
                    os._exit(17)
                return httpx2.Response(204 if method == "DELETE" else 200, content=b"")

        return httpx2.Response(501, content=b"unsupported method in fake server")


def _authorization() -> AuthorizationEvidence:
    return AuthorizationEvidence(
        policy_version="test-policy-v1",
        matched_rule_ids=("grant-family-calendar",),
    )


def _base() -> EventBaseVersion:
    return EventBaseVersion(version=EventVersion(f'"{SEED_ETAG}"'), sequence=0)


def _configure(system_db: Path) -> None:
    config: DBOSConfig = {
        "name": "ada-caldav-change-hard-crash-regression",
        "application_version": "test",
        "run_admin_server": False,
        "log_level": "WARNING",
        "console_log_level": "WARNING",
        "system_database_url": f"sqlite:///{system_db}",
    }
    DBOS(config=config)


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: dbos_caldav_change_crash_worker.py "
            "<update|cancel> <seed|start|recover> "
            "<system-db> <provider-db> <operation-id>"
        )

    kind, phase = sys.argv[1], sys.argv[2]
    system_db, provider_db = Path(sys.argv[3]), Path(sys.argv[4])
    operation_id = sys.argv[5]

    if phase == "seed":
        with closing(_connect(provider_db)) as con:
            con.execute(
                "INSERT OR REPLACE INTO resources(path, body, etag) VALUES (?, ?, ?)",
                (RESOURCE_PATH, SEED_BODY, SEED_ETAG),
            )
            con.commit()
        return

    _configure(system_db)
    server = _PersistentFakeCalDAVServer(
        provider_db, crash_after_commit=phase == "start"
    )
    calendar = CalDAVCalendarAdapter(
        base_url=BASE_URL,
        auth=("ada-fake@example.test", "fake-app-password"),
        calendars=(
            CalendarRef(
                calendar_id="family",
                provider_collection=COLLECTION_PATH,
                audience=CalendarAudience.FAMILY,
                access_mode=CalendarAccessMode.WRITE,
            ),
        ),
        profile=IONOS_PROFILE,
        transport=httpx2.MockTransport(server),
        clock=lambda: datetime.fromisoformat("2026-10-01T00:00:00+00:00"),
    )
    durable = DBOSDurableCalendarActions(
        calendar,
        instance_name="calendar-actions-caldav-change-hard-crash",
    )
    DBOS.launch()

    event_ref = EventRef(calendar_id="family", resource_name=RESOURCE_NAME)

    if phase == "start":
        if kind == "update":
            durable.update_calendar_event(
                DurableCalendarUpdate(
                    operation_id=OperationId(operation_id),
                    proposal=UpdateCalendarEventProposal(
                        event_ref=event_ref,
                        base_version=_base(),
                        changes=CalendarEventChanges(title="Synthetic new title"),
                    ),
                    authorization=_authorization(),
                )
            )
        else:
            durable.cancel_calendar_event(
                DurableCalendarCancel(
                    operation_id=OperationId(operation_id),
                    proposal=CancelCalendarEventProposal(
                        event_ref=event_ref, base_version=_base()
                    ),
                    authorization=_authorization(),
                )
            )
        raise AssertionError("the provider commit should hard-crash the process")

    if phase == "recover":
        handle = DBOS.retrieve_workflow(operation_id)
        result = handle.get_result(polling_interval_sec=0.05)
        status = handle.get_status()
        print(
            json.dumps(
                {
                    "workflow_status": status.status,
                    "provider_status": result.provider.status.value,
                    "business_status": result.business.status.value,
                    "error_code": result.provider.error_code,
                }
            )
        )
        DBOS.destroy()
        return

    raise SystemExit(f"unknown phase: {phase}")


if __name__ == "__main__":
    main()
