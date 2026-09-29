from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

WORKER = Path(__file__).with_name("dbos_caldav_change_crash_worker.py")
RESOURCE_PATH = "/caldav/family/seeded-event.ics"


def call_counts(provider_db: Path) -> dict[str, int]:
    with closing(sqlite3.connect(provider_db)) as con:
        rows = con.execute("SELECT kind, COUNT(*) FROM calls GROUP BY kind").fetchall()
    return {kind: int(count) for kind, count in rows}


def stored_resource(provider_db: Path) -> tuple[bytes, str] | None:
    with closing(sqlite3.connect(provider_db)) as con:
        row = con.execute(
            "SELECT body, etag FROM resources WHERE path = ?", (RESOURCE_PATH,)
        ).fetchone()
    return (bytes(row[0]), str(row[1])) if row else None


class CalDAVChangeCrashRecoveryTests(unittest.TestCase):
    """Hard-crash regressions for the CalDAV update/cancel path (S4)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.system_db = root / "dbos.sqlite"
        self.provider_db = root / "provider.sqlite"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_worker(
        self, kind: str, phase: str, operation_id: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(WORKER),
                kind,
                phase,
                str(self.system_db),
                str(self.provider_db),
                operation_id,
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def recovered_payload(self, operation_id: str, kind: str) -> dict[str, object]:
        recovered = self.run_worker(kind, "recover", operation_id)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        lines = [
            line for line in recovered.stdout.splitlines() if line.strip().startswith("{")
        ]
        self.assertTrue(lines, recovered.stdout)
        return json.loads(lines[-1])

    def test_update_hard_crash_after_commit_recovers_committed_without_rewrite(
        self,
    ) -> None:
        operation_id = "op-caldav-update-hard-crash"
        self.assertEqual(self.run_worker("update", "seed", operation_id).returncode, 0)

        crashed = self.run_worker("update", "start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

        payload = self.recovered_payload(operation_id, "update")

        self.assertEqual(payload["workflow_status"], "SUCCESS")
        self.assertEqual(payload["provider_status"], "committed")
        self.assertEqual(payload["business_status"], "committed")
        # The replay found this operation's marker on the event instead of
        # reporting a conflict against its own write, and wrote nothing more.
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)
        body, etag = stored_resource(self.provider_db)  # type: ignore[misc]
        self.assertEqual(etag, "e2")
        self.assertIn(b"SUMMARY:Synthetic new title", body)
        self.assertIn(b"SEQUENCE:1", body)

    def test_cancel_hard_crash_after_commit_recovers_as_absent_without_second_delete(
        self,
    ) -> None:
        operation_id = "op-caldav-cancel-hard-crash"
        self.assertEqual(self.run_worker("cancel", "seed", operation_id).returncode, 0)

        crashed = self.run_worker("cancel", "start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(call_counts(self.provider_db).get("delete"), 1)

        payload = self.recovered_payload(operation_id, "cancel")

        # Ada cannot prove the delete was its own: it reports that the event
        # no longer exists, exactly once and without a second DELETE.
        self.assertEqual(payload["workflow_status"], "SUCCESS")
        self.assertEqual(payload["provider_status"], "failed")
        self.assertEqual(payload["error_code"], "event_absent")
        self.assertEqual(call_counts(self.provider_db).get("delete"), 1)
        self.assertIsNone(stored_resource(self.provider_db))


if __name__ == "__main__":
    unittest.main()
