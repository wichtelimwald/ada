from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProviderResult:
    committed: bool
    provider_reference: str | None


class FakeProvider:
    """Separate durable store simulating an external provider."""

    def __init__(self, path: Path, *, supports_reconciliation: bool = True) -> None:
        self.path = path
        self.supports_reconciliation = supports_reconciliation
        with sqlite3.connect(self.path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS effects (
                    operation_id TEXT PRIMARY KEY,
                    provider_reference TEXT NOT NULL
                )
                """
            )

    def create(self, operation_id: str) -> ProviderResult:
        ref = f"evt-{operation_id}"
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT OR IGNORE INTO effects(operation_id, provider_reference) VALUES (?, ?)",
                (operation_id, ref),
            )
        return ProviderResult(True, ref)

    def reconcile(self, operation_id: str) -> ProviderResult | None:
        if not self.supports_reconciliation:
            return None
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT provider_reference FROM effects WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return ProviderResult(False, None)
        return ProviderResult(True, row[0])

    def effect_count(self, operation_id: str) -> int:
        with sqlite3.connect(self.path) as con:
            return int(
                con.execute(
                    "SELECT COUNT(*) FROM effects WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()[0]
            )
