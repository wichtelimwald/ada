from __future__ import annotations

import json
from contextlib import closing
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dbos import DBOS, DBOSConfig

from ada.adapters.dbos_durable_actions import DBOSDurableCalendarActions
from ada.core.action_outcomes import AuthorizationEvidence, OperationId, ProviderCapability
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import (
    CalendarCreateResult,
    CalendarCreateStatus,
    CalendarEvent,
)
from ada.ports.durable_action import DurableCalendarCreate


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS effects (
            operation_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            title TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            calendar_id TEXT NOT NULL,
            location TEXT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


class PersistentCrashCalendarAdapter:
    """Process-persistent provider used only by the hard-crash regression test."""

    def __init__(self, provider_db: Path, *, crash_after_commit: bool) -> None:
        self._provider_db = provider_db
        self._crash_after_commit = crash_after_commit
        with closing(_connect(provider_db)):
            pass

    @property
    def create_capability(self) -> ProviderCapability:
        return ProviderCapability.RECONCILABLE

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[CalendarEvent, ...]:
        del start, end
        return ()

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        with closing(_connect(self._provider_db)) as con:
            con.execute("INSERT INTO calls(kind) VALUES ('reconcile')")
            row = con.execute(
                """
                SELECT event_id, title, start, end, calendar_id, location
                  FROM effects
                 WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()
            con.commit()

        if row is None:
            return None
        return CalendarEvent(
            event_id=str(row[0]),
            title=str(row[1]),
            start=datetime.fromisoformat(str(row[2])),
            end=datetime.fromisoformat(str(row[3])),
            calendar_id=str(row[4]),
            location=None if row[5] is None else str(row[5]),
        )

    def create_event(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarCreateResult:
        event = CalendarEvent(
            event_id=f"persistent-{operation_id}",
            title=proposal.title,
            start=proposal.start,
            end=proposal.end,
            calendar_id=proposal.calendar_id,
            location=proposal.location,
        )
        with closing(_connect(self._provider_db)) as con:
            con.execute("INSERT INTO calls(kind) VALUES ('create')")
            con.execute(
                """
                INSERT INTO effects(
                    operation_id, event_id, title, start, end, calendar_id, location
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    event.event_id,
                    event.title,
                    event.start.isoformat(),
                    event.end.isoformat(),
                    event.calendar_id,
                    event.location,
                ),
            )
            con.commit()

        # Hard process death after the provider commit but before the DBOS step
        # wrapper can checkpoint the returned result.
        if self._crash_after_commit:
            os._exit(17)

        return CalendarCreateResult(
            status=CalendarCreateStatus.COMMITTED,
            event=event,
        )


def _request(operation_id: str) -> DurableCalendarCreate:
    return DurableCalendarCreate(
        operation_id=OperationId(operation_id),
        proposal=CreateCalendarEventProposal(
            title="Synthetic crash recovery event",
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
        "name": "ada-hard-crash-regression",
        "application_version": "test",
        "run_admin_server": False,
        "log_level": "WARNING",
        "console_log_level": "WARNING",
        "system_database_url": f"sqlite:///{system_db}",
    }
    DBOS(config=config)


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: dbos_crash_worker.py <start|recover> "
            "<system-db> <provider-db> <operation-id>"
        )

    phase = sys.argv[1]
    system_db = Path(sys.argv[2])
    provider_db = Path(sys.argv[3])
    operation_id = sys.argv[4]

    _configure(system_db)
    calendar = PersistentCrashCalendarAdapter(
        provider_db,
        crash_after_commit=phase == "start",
    )
    durable = DBOSDurableCalendarActions(
        calendar,
        instance_name="calendar-actions-hard-crash",
    )
    DBOS.launch()

    if phase == "start":
        durable.create_calendar_event(_request(operation_id))
        raise AssertionError("first provider commit should hard-crash the process")

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
                    "provider_reference": result.provider.provider_reference,
                }
            )
        )
        DBOS.destroy()
        return

    raise SystemExit(f"unknown phase: {phase}")


if __name__ == "__main__":
    main()
