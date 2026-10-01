from __future__ import annotations

import dataclasses
import json
from contextlib import closing
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import httpx2
from dbos import DBOS, DBOSConfig

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.core.action_outcomes import (
    AuthorizationEvidence,
    OperationId,
    ProviderCapability,
)
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef
from ada.ports.durable_action import DurableCalendarCreate

BASE_URL = "https://dav.mailbusiness.ionos.test"
COLLECTION_PATH = "/caldav/family/"


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS resources ("
        "path TEXT PRIMARY KEY, body BLOB NOT NULL)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS calls ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL)"
    )
    con.commit()
    return con


class _PersistentFakeCalDAVServer:
    """Process-persistent fake CalDAV server for the hard-crash regression test.

    Mirrors ``PersistentCrashCalendarAdapter`` in ``dbos_crash_worker.py`` but
    speaks the CalDAV wire protocol so it can sit behind the real
    ``CalDAVCalendarAdapter`` rather than a hand-rolled ``CalendarPort``.
    """

    def __init__(
        self,
        provider_db: Path,
        *,
        crash_after_commit: bool,
        fail_method: str | None = None,
    ) -> None:
        self._provider_db = provider_db
        self._crash_after_commit = crash_after_commit
        # An HTTP method whose connection attempt is refused before anything
        # is sent (a provider that is unreachable *now*).
        self._fail_method = fail_method
        with closing(_connect(provider_db)):
            pass

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        method = request.method
        path = request.url.path

        if method == self._fail_method:
            raise httpx2.ConnectError("simulated unreachable provider")

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

        if method == "GET":
            with closing(_connect(self._provider_db)) as con:
                con.execute("INSERT INTO calls(kind) VALUES ('get')")
                row = con.execute(
                    "SELECT body FROM resources WHERE path = ?", (path,)
                ).fetchone()
                con.commit()
            if row is None:
                return httpx2.Response(404, content=b"not found")
            return httpx2.Response(
                200,
                content=row[0],
                headers={"Content-Type": "text/calendar", "ETag": '"e1"'},
            )

        if method == "PUT":
            with closing(_connect(self._provider_db)) as con:
                con.execute("INSERT INTO calls(kind) VALUES ('put')")
                existing = con.execute(
                    "SELECT 1 FROM resources WHERE path = ?", (path,)
                ).fetchone()
                if (
                    request.headers.get("if-none-match") == "*"
                    and existing is not None
                ):
                    con.commit()
                    return httpx2.Response(412, content=b"precondition failed")
                con.execute(
                    "INSERT INTO resources(path, body) VALUES (?, ?) "
                    "ON CONFLICT(path) DO UPDATE SET body = excluded.body",
                    (path, request.content),
                )
                con.commit()

            # Hard process death after the provider commit but before the DBOS
            # step wrapper can checkpoint the returned result.
            if self._crash_after_commit:
                os._exit(17)
            return httpx2.Response(201, content=b"")

        return httpx2.Response(501, content=b"unsupported method in fake server")


def _request(operation_id: str) -> DurableCalendarCreate:
    return DurableCalendarCreate(
        operation_id=OperationId(operation_id),
        proposal=CreateCalendarEventProposal(
            title="Synthetic CalDAV crash recovery event",
            start=datetime.fromisoformat("2026-10-12T16:00:00+00:00"),
            end=datetime.fromisoformat("2026-10-12T16:30:00+00:00"),
            calendar_id="family",
            location="School North",
        ),
        authorization=AuthorizationEvidence(
            policy_version="test-policy-v1",
            matched_rule_ids=("grant-family-calendar",),
        ),
    )


def _configure(system_db: Path) -> None:
    config: DBOSConfig = {
        "name": "ada-caldav-hard-crash-regression",
        "application_version": "test",
        "run_admin_server": False,
        "log_level": "WARNING",
        "console_log_level": "WARNING",
        "system_database_url": f"sqlite:///{system_db}",
    }
    DBOS(config=config)


def _print_result(
    result: object | None,
    *,
    workflow_status: str,
    raised: BaseException | None = None,
) -> None:
    payload: dict[str, object] = {"workflow_status": workflow_status}
    if raised is not None:
        payload["raised"] = type(raised).__name__
    else:
        payload["provider_status"] = result.provider.status.value  # type: ignore[attr-defined]
        payload["business_status"] = result.business.status.value  # type: ignore[attr-defined]
        payload["error_code"] = result.provider.error_code  # type: ignore[attr-defined]
    print(json.dumps(payload))


def main() -> None:
    if len(sys.argv) not in (5, 6):
        raise SystemExit(
            "usage: dbos_caldav_crash_worker.py <start|recover|run> "
            "<system-db> <provider-db> <operation-id> [variant]"
        )

    phase = sys.argv[1]
    system_db = Path(sys.argv[2])
    provider_db = Path(sys.argv[3])
    operation_id = sys.argv[4]
    # Variants describe what the process sees *now* (the restarted process for
    # ``recover``, the only process for ``run``):
    #   read-only / unconfigured -- the calendar is no longer writable / known;
    #   put-unreachable          -- a create PUT cannot be sent;
    #   propfind-fails / get-fails -- the collection lookup / reads fail;
    #   no-capability            -- the provider declares create not recoverable.
    variant = sys.argv[5] if len(sys.argv) == 6 else ""

    _configure(system_db)
    server = _PersistentFakeCalDAVServer(
        provider_db,
        crash_after_commit=phase == "start",
        fail_method={
            "put-unreachable": "PUT",
            "propfind-fails": "PROPFIND",
            "get-fails": "GET",
        }.get(variant),
    )
    profile = IONOS_PROFILE
    if variant == "no-capability":
        profile = dataclasses.replace(
            IONOS_PROFILE, create_capability=ProviderCapability.NONE
        )
    calendar = CalDAVCalendarAdapter(
        base_url=BASE_URL,
        auth=("ada-fake@example.test", "fake-app-password"),
        calendars=(
            CalendarRef(
                calendar_id="elsewhere" if variant == "unconfigured" else "family",
                provider_collection=COLLECTION_PATH,
                audience=CalendarAudience.FAMILY,
                access_mode=(
                    CalendarAccessMode.READ
                    if variant == "read-only"
                    else CalendarAccessMode.WRITE
                ),
            ),
        ),
        profile=profile,
        transport=httpx2.MockTransport(server),
    )
    durable = DBOSDurableCalendarActions(
        calendar,
        instance_name="calendar-actions-caldav-hard-crash",
    )
    DBOS.launch()

    if phase == "start":
        durable.create_calendar_event(_request(operation_id))
        raise AssertionError("first provider commit should hard-crash the process")

    if phase == "run":
        try:
            result = durable.create_calendar_event(_request(operation_id))
        except Exception as exc:  # noqa: BLE001 - the test inspects what escapes
            _print_result(
                None,
                workflow_status=DBOS.retrieve_workflow(operation_id).get_status().status,
                raised=exc,
            )
        else:
            _print_result(result, workflow_status="SUCCESS")
        DBOS.destroy()
        return

    if phase == "recover":
        handle = DBOS.retrieve_workflow(operation_id)
        try:
            result = handle.get_result(polling_interval_sec=0.05)
        except Exception as exc:  # noqa: BLE001 - the test inspects what escapes
            _print_result(
                None, workflow_status=handle.get_status().status, raised=exc
            )
        else:
            _print_result(result, workflow_status=handle.get_status().status)
        DBOS.destroy()
        return

    raise SystemExit(f"unknown phase: {phase}")


if __name__ == "__main__":
    main()
