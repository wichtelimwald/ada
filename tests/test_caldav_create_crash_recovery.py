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

    A DBOS step that crashes after the provider committed is executed again on
    recovery and, from the inside, looks identical to a first execution. Whatever
    the replay then observes must never be reported as a confirmed non-commit
    just because *this* execution did not send (or could not send) a create
    (ADR-0009 section 6, ADR-0005).
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.system_db = root / "dbos.sqlite"
        self.provider_db = root / "provider.sqlite"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_worker(
        self, phase: str, operation_id: str, variant: str = ""
    ) -> subprocess.CompletedProcess[str]:
        args = [
            sys.executable,
            str(WORKER),
            phase,
            str(self.system_db),
            str(self.provider_db),
            operation_id,
        ]
        if variant:
            args.append(variant)
        return subprocess.run(
            args, text=True, capture_output=True, check=False, timeout=30
        )

    def payload_of(
        self, completed: subprocess.CompletedProcess[str]
    ) -> dict[str, object]:
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = [
            line
            for line in completed.stdout.splitlines()
            if line.strip().startswith("{")
        ]
        self.assertTrue(lines, completed.stdout)
        return json.loads(lines[-1])

    def crash_after_commit(self, operation_id: str) -> None:
        crashed = self.run_worker("start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(provider_counts(self.provider_db), (1, 1, 0))

    def assert_unproven(self, payload: dict[str, object], error_code: str) -> None:
        """Ada's effect is unproven: ambiguous, never a confirmed non-commit."""

        self.assertEqual(payload["workflow_status"], "SUCCESS")
        self.assertEqual(payload["provider_status"], "ambiguous")
        self.assertEqual(payload["business_status"], "ambiguous")
        self.assertEqual(payload["error_code"], error_code)

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

    # -- replay after a possible earlier commit -----------------------------

    def test_replay_refused_before_sending_is_not_a_confirmed_failure(self) -> None:
        # The earlier execution committed. The restarted process cannot send
        # another create (the calendar is no longer writable or known, the
        # provider is unreachable or no longer declared recoverable): that is
        # no evidence the *earlier* create did not apply.
        cases = {
            "read-only": "calendar_not_writable_after_possible_send",
            "unconfigured": "calendar_not_configured_after_possible_send",
            "put-unreachable": "not_attempted_after_possible_send",
            "propfind-fails": "collection_unavailable_after_possible_send",
            "no-capability": "provider_not_recoverable_after_possible_send",
        }
        for variant, error_code in cases.items():
            with self.subTest(variant):
                self.tearDown()
                self.setUp()
                operation_id = f"op-caldav-replay-{variant}"
                self.crash_after_commit(operation_id)

                payload = self.payload_of(
                    self.run_worker("recover", operation_id, variant)
                )

                self.assert_unproven(payload, error_code)
                # No duplicate event, and the replay sent nothing that could
                # have created one.
                resources, puts, _gets = provider_counts(self.provider_db)
                self.assertEqual((resources, puts), (1, 1))

    def test_replay_whose_reconciliation_cannot_read_stays_ambiguous(self) -> None:
        # Positive control: the existing 412 path. The replay's create-only
        # PUT is refused (the earlier commit exists), the proving GET fails:
        # unresolved, never a failure and never a second event.
        operation_id = "op-caldav-replay-412-unreadable"
        self.crash_after_commit(operation_id)

        payload = self.payload_of(
            self.run_worker("recover", operation_id, "get-fails")
        )

        self.assert_unproven(payload, "precondition_failed_unresolved")
        resources, _puts, _gets = provider_counts(self.provider_db)
        self.assertEqual(resources, 1)

    # -- genuinely fresh requests keep their definite outcomes --------------

    def test_fresh_refusal_before_sending_is_a_definite_failure(self) -> None:
        # Nothing was ever sent for a first execution, so a refusal before
        # sending proves a non-commit and keeps its definite report.
        cases = {
            "read-only": "calendar_not_writable",
            "unconfigured": "calendar_not_configured",
            "put-unreachable": "not_attempted",
            "propfind-fails": "collection_unavailable",
            "no-capability": "provider_not_recoverable",
        }
        for variant, error_code in cases.items():
            with self.subTest(variant):
                self.tearDown()
                self.setUp()
                operation_id = f"op-caldav-fresh-{variant}"

                payload = self.payload_of(
                    self.run_worker("run", operation_id, variant)
                )

                self.assertEqual(payload["workflow_status"], "SUCCESS")
                self.assertEqual(payload["provider_status"], "failed")
                self.assertEqual(payload["business_status"], "failed")
                self.assertEqual(payload["error_code"], error_code)
                self.assertEqual(provider_counts(self.provider_db), (0, 0, 0))

    def test_fresh_create_commits_once(self) -> None:
        operation_id = "op-caldav-fresh-commit"

        payload = self.payload_of(self.run_worker("run", operation_id))

        self.assertEqual(payload["provider_status"], "committed")
        self.assertEqual(provider_counts(self.provider_db), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
