from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WORKER = Path(__file__).with_name("dbos_worker.py")


def provider_counts(
    provider_db: Path,
    operation_id: str,
    mode: str,
) -> tuple[int, int]:
    with sqlite3.connect(provider_db) as con:
        effects = int(
            con.execute(
                "SELECT COUNT(*) FROM effects WHERE operation_id = ? AND mode = ?",
                (operation_id, mode),
            ).fetchone()[0]
        )
        attempts = int(
            con.execute(
                "SELECT COUNT(*) FROM attempts WHERE operation_id = ? AND mode = ?",
                (operation_id, mode),
            ).fetchone()[0]
        )
    return effects, attempts


class DBOSActionRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.system_db = root / "dbos.sqlite3"
        self.provider_db = root / "provider.sqlite3"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_worker(self, phase: str, operation_id: str) -> subprocess.CompletedProcess[str]:
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

    def test_crash_recovery_reexecutes_step_but_reconciliation_prevents_duplicate(self) -> None:
        operation_id = "op-reconciled"

        crashed = self.run_worker("start-reconciled", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(
            provider_counts(self.provider_db, operation_id, "reconciled"),
            (1, 1),
        )

        recovered = self.run_worker("recover", operation_id)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        json_lines = [
            line for line in recovered.stdout.splitlines()
            if line.strip().startswith("{")
        ]
        self.assertTrue(json_lines, recovered.stdout)
        payload = json.loads(json_lines[-1])

        self.assertEqual(payload["workflow_id"], operation_id)
        self.assertEqual(payload["result"], f"evt-{operation_id}")

        # DBOS re-executed the uncheckpointed external step. Ada/provider
        # reconciliation prevented a second external effect.
        self.assertEqual(
            provider_counts(self.provider_db, operation_id, "reconciled"),
            (1, 2),
        )

    def test_dbos_alone_does_not_make_unreconcilable_external_step_exactly_once(self) -> None:
        operation_id = "op-unsafe"

        crashed = self.run_worker("start-unsafe", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(
            provider_counts(self.provider_db, operation_id, "unsafe"),
            (1, 1),
        )

        recovered = self.run_worker("recover", operation_id)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)

        # Expected boundary evidence: the uncheckpointed step is retried and
        # produces a second provider effect because the provider offers no
        # idempotency/reconciliation mechanism.
        self.assertEqual(
            provider_counts(self.provider_db, operation_id, "unsafe"),
            (2, 2),
        )

    def test_workflow_id_is_an_idempotency_key_after_completion(self) -> None:
        operation_id = "op-idempotent-workflow"

        self.assertEqual(
            self.run_worker("start-reconciled", operation_id).returncode,
            17,
        )
        recovered = self.run_worker("recover", operation_id)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)

        before = provider_counts(self.provider_db, operation_id, "reconciled")
        replay = self.run_worker("reinvoke-reconciled", operation_id)
        self.assertEqual(replay.returncode, 0, replay.stderr)
        after = provider_counts(self.provider_db, operation_id, "reconciled")

        self.assertEqual(before, (1, 2))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
