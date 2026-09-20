from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WORKER = Path(__file__).with_name("dbos_crash_worker.py")


def provider_counts(provider_db: Path) -> tuple[int, int, int]:
    with sqlite3.connect(provider_db) as con:
        effects = int(con.execute("SELECT COUNT(*) FROM effects").fetchone()[0])
        creates = int(
            con.execute(
                "SELECT COUNT(*) FROM calls WHERE kind = 'create'"
            ).fetchone()[0]
        )
        reconciles = int(
            con.execute(
                "SELECT COUNT(*) FROM calls WHERE kind = 'reconcile'"
            ).fetchone()[0]
        )
    return effects, creates, reconciles


class DurableCalendarCrashRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.system_db = root / "dbos.sqlite"
        self.provider_db = root / "provider.sqlite"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_worker(
        self,
        phase: str,
        operation_id: str,
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
        operation_id = "op-process-hard-crash"

        crashed = self.run_worker("start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(
            provider_counts(self.provider_db),
            (1, 1, 1),
        )

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
        self.assertEqual(
            payload["provider_reference"],
            f"persistent-{operation_id}",
        )

        # DBOS re-executed the uncheckpointed step after restart. The step
        # reconciled first, so the real provider write was not repeated.
        self.assertEqual(
            provider_counts(self.provider_db),
            (1, 1, 2),
        )


if __name__ == "__main__":
    unittest.main()
