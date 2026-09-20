from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TERMINAL = {"denied", "failed", "committed", "ambiguous"}
ALLOWED = {
    "proposed": {"denied", "authorized"},
    "authorized": {"executing", "failed"},
    "executing": {"committed", "failed", "ambiguous"},
    "ambiguous": {"committed", "failed"},
    "denied": set(),
    "failed": set(),
    "committed": set(),
}


@dataclass(frozen=True, slots=True)
class Operation:
    operation_id: str
    action_kind: str
    state: str
    provider_kind: str
    provider_reference: str | None


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    action_kind TEXT NOT NULL,
                    state TEXT NOT NULL,
                    provider_kind TEXT NOT NULL,
                    provider_reference TEXT
                );

                CREATE TABLE IF NOT EXISTS transitions (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES operations(operation_id)
                );
                """
            )

    def create(self, operation_id: str, action_kind: str, provider_kind: str) -> None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO operations(operation_id, action_kind, state, provider_kind) VALUES (?, ?, 'proposed', ?)",
                (operation_id, action_kind, provider_kind),
            )
            con.execute(
                "INSERT INTO transitions(operation_id, from_state, to_state) VALUES (?, NULL, 'proposed')",
                (operation_id,),
            )
            con.commit()

    def get(self, operation_id: str) -> Operation:
        with self._connect() as con:
            row = con.execute(
                "SELECT operation_id, action_kind, state, provider_kind, provider_reference "
                "FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(operation_id)
        return Operation(*row)

    def transition(
        self,
        operation_id: str,
        expected_from: str,
        to_state: str,
        *,
        provider_reference: str | None = None,
    ) -> None:
        if to_state not in ALLOWED.get(expected_from, set()):
            raise ValueError(f"illegal transition {expected_from} -> {to_state}")

        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            cur = con.execute(
                """
                UPDATE operations
                   SET state = ?,
                       provider_reference = COALESCE(?, provider_reference)
                 WHERE operation_id = ?
                   AND state = ?
                """,
                (to_state, provider_reference, operation_id, expected_from),
            )
            if cur.rowcount != 1:
                con.rollback()
                raise RuntimeError("operation state changed concurrently or operation missing")
            con.execute(
                "INSERT INTO transitions(operation_id, from_state, to_state) VALUES (?, ?, ?)",
                (operation_id, expected_from, to_state),
            )
            con.commit()

    def recoverable(self) -> list[Operation]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT operation_id, action_kind, state, provider_kind, provider_reference
                  FROM operations
                 WHERE state IN ('authorized', 'executing', 'ambiguous')
                 ORDER BY operation_id
                """
            ).fetchall()
        return [Operation(*row) for row in rows]
