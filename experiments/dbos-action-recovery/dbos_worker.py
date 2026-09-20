from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from dbos import DBOS, SetWorkflowID


def _connect_provider(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            provider_reference TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL,
            mode TEXT NOT NULL
        )
        """
    )
    return con


def _attempt_number(con: sqlite3.Connection, operation_id: str, mode: str) -> int:
    con.execute(
        "INSERT INTO attempts(operation_id, mode) VALUES (?, ?)",
        (operation_id, mode),
    )
    con.commit()
    return int(
        con.execute(
            "SELECT COUNT(*) FROM attempts WHERE operation_id = ? AND mode = ?",
            (operation_id, mode),
        ).fetchone()[0]
    )


@DBOS.step()
def reconciled_provider_step(provider_db: str, operation_id: str) -> str:
    """External write with Ada-style reconciliation by stable operation ID."""
    with _connect_provider(provider_db) as con:
        attempt = _attempt_number(con, operation_id, "reconciled")

        existing = con.execute(
            """
            SELECT provider_reference
              FROM effects
             WHERE operation_id = ? AND mode = 'reconciled'
             ORDER BY id
             LIMIT 1
            """,
            (operation_id,),
        ).fetchone()
        if existing is not None:
            return str(existing[0])

        reference = f"evt-{operation_id}"
        con.execute(
            """
            INSERT INTO effects(operation_id, mode, provider_reference)
            VALUES (?, 'reconciled', ?)
            """,
            (operation_id, reference),
        )
        con.commit()

        # Crash after the provider committed but before DBOS can checkpoint
        # this step result. On recovery DBOS will execute the step again.
        if attempt == 1:
            os._exit(17)

        return reference


@DBOS.step()
def unsafe_provider_step(provider_db: str, operation_id: str) -> str:
    """External write with neither idempotency nor reconciliation."""
    with _connect_provider(provider_db) as con:
        attempt = _attempt_number(con, operation_id, "unsafe")
        reference = f"effect-{operation_id}-{attempt}"
        con.execute(
            """
            INSERT INTO effects(operation_id, mode, provider_reference)
            VALUES (?, 'unsafe', ?)
            """,
            (operation_id, reference),
        )
        con.commit()

        if attempt == 1:
            os._exit(17)

        return reference


@DBOS.workflow()
def reconciled_action(provider_db: str, operation_id: str) -> str:
    return reconciled_provider_step(provider_db, operation_id)


@DBOS.workflow()
def unsafe_action(provider_db: str, operation_id: str) -> str:
    return unsafe_provider_step(provider_db, operation_id)


def configure(system_db: str) -> None:
    DBOS(
        config={
            "name": "ada-dbos-action-recovery-probe",
            "application_version": "probe-v1",
            "system_database_url": f"sqlite:///{system_db}",
        }
    )
    DBOS.launch()


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: dbos_worker.py <start-reconciled|start-unsafe|recover|reinvoke-reconciled> "
            "<system-db> <provider-db> <operation-id>"
        )

    phase, system_db, provider_db, operation_id = sys.argv[1:]
    configure(system_db)

    if phase == "start-reconciled":
        with SetWorkflowID(operation_id):
            reconciled_action(provider_db, operation_id)
        raise AssertionError("first provider attempt should hard-crash")

    if phase == "start-unsafe":
        with SetWorkflowID(operation_id):
            unsafe_action(provider_db, operation_id)
        raise AssertionError("first provider attempt should hard-crash")

    if phase == "recover":
        handle = DBOS.retrieve_workflow(operation_id)
        result = handle.get_result(polling_interval_sec=0.05)
        status = handle.get_status()
        print(
            json.dumps(
                {
                    "workflow_id": operation_id,
                    "result": result,
                    "status": status.status,
                }
            )
        )
        DBOS.destroy()
        return

    if phase == "reinvoke-reconciled":
        with SetWorkflowID(operation_id):
            result = reconciled_action(provider_db, operation_id)
        print(json.dumps({"workflow_id": operation_id, "result": result}))
        DBOS.destroy()
        return

    raise SystemExit(f"unknown phase: {phase}")


if __name__ == "__main__":
    main()
