from __future__ import annotations

import json
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WORKER = Path(__file__).with_name("dbos_caldav_crash_worker.py")


def provider_counts(provider_db: Path) -> tuple[int, int, int]:
    with closing(sqlite3.connect(provider_db)) as con:
        resources = int(
            con.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        )
        puts = int(
            con.execute("SELECT COUNT(*) FROM calls WHERE kind = 'put'").fetchone()[0]
        )
        gets = int(
            con.execute("SELECT COUNT(*) FROM calls WHERE kind = 'get'").fetchone()[0]
        )
    return resources, puts, gets


class CalDAVCreateCrashRecoveryTests(unittest.TestCase):
    """Hard-crash regression for the real CalDAV create path (S3).

    Mirrors ``test_durable_calendar_crash_recovery.py`` but drives the actual
    ``CalDAVCalendarAdapter`` over its create-only PUT / marker-reconciliation
    logic instead of a hand-rolled ``CalendarPort``.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.system_db = root / "dbos.sqlite"
        self.provider_db = root / "provider.sqlite"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_worker(
        self, phase: str, operation_id: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(WORKER),
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

    def test_hard_crash_after_provider_commit_recovers_without_duplicate(self) -> None:
        operation_id = "op-caldav-hard-crash"

        crashed = self.run_worker("start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(provider_counts(self.provider_db), (1, 1, 0))

        recovered = self.run_worker("recover", operation_id)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        json_lines = [
            line
            for line in recovered.stdout.splitlines()
            if line.strip().startswith("{")
        ]
        self.assertTrue(json_lines, recovered.stdout)
        payload = json.loads(json_lines[-1])

        self.assertEqual(payload["workflow_status"], "SUCCESS")
        self.assertEqual(payload["provider_status"], "committed")
        self.assertEqual(payload["business_status"], "committed")

        # DBOS re-executed the uncheckpointed step after restart: exactly one
        # resource exists, and the second PUT attempt got 412 and was
        # reconciled via GET + operation marker rather than blindly retried
        # as a fresh write.
        self.assertEqual(provider_counts(self.provider_db), (1, 2, 1))


if __name__ == "__main__":
    unittest.main()
