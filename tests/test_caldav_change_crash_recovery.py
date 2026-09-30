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


def provider_human_edit(provider_db: Path, *, keep_marker: bool) -> None:
    """A person edits the event in webmail: a new ETag and a changed title.

    ``keep_marker=False`` also drops Ada's operation marker, as a client that
    rewrites the resource without unknown ``X-`` properties would.
    """

    with closing(sqlite3.connect(provider_db)) as con:
        body, etag = con.execute(
            "SELECT body, etag FROM resources WHERE path = ?", (RESOURCE_PATH,)
        ).fetchone()
        body = bytes(body).replace(b"SUMMARY:", b"SUMMARY:Edited by a human - ")
        if not keep_marker:
            body = body.replace(b"X-ADA-OPERATION-MARKER", b"X-OTHER-PROPERTY")
        con.execute(
            "UPDATE resources SET body = ?, etag = ? WHERE path = ?",
            (body, f"e{int(etag[1:]) + 1}", RESOURCE_PATH),
        )
        con.commit()


def provider_delete(provider_db: Path) -> None:
    with closing(sqlite3.connect(provider_db)) as con:
        con.execute("DELETE FROM resources WHERE path = ?", (RESOURCE_PATH,))
        con.commit()


def stored_resource(provider_db: Path) -> tuple[bytes, str] | None:
    with closing(sqlite3.connect(provider_db)) as con:
        row = con.execute(
            "SELECT body, etag FROM resources WHERE path = ?", (RESOURCE_PATH,)
        ).fetchone()
    return (bytes(row[0]), str(row[1])) if row else None


class CalDAVChangeCrashRecoveryTests(unittest.TestCase):
    """Hard-crash and fresh-run regressions for the CalDAV update/cancel path.

    A DBOS step that crashes after the provider committed is re-executed on
    recovery. Whatever the replay then observes must never be reported as a
    stronger conclusion about Ada's own effect than the evidence proves
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
        self, kind: str, phase: str, operation_id: str, variant: str = ""
    ) -> subprocess.CompletedProcess[str]:
        args = [
            sys.executable,
            str(WORKER),
            kind,
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

    def payload_of(self, completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = [
            line for line in completed.stdout.splitlines() if line.strip().startswith("{")
        ]
        self.assertTrue(lines, completed.stdout)
        return json.loads(lines[-1])

    def seed_and_crash(self, kind: str, operation_id: str) -> None:
        self.assertEqual(self.run_worker(kind, "seed", operation_id).returncode, 0)
        crashed = self.run_worker(kind, "start", operation_id)
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertEqual(call_counts(self.provider_db).get("put" if kind == "update" else "delete"), 1)

    def assert_unproven(self, payload: dict[str, object], error_code: str) -> None:
        """Ada's effect is unproven: ambiguous, never a confirmed non-commit."""

        self.assertEqual(payload["workflow_status"], "SUCCESS")
        self.assertEqual(payload["provider_status"], "ambiguous")
        self.assertEqual(payload["business_status"], "ambiguous")
        self.assertEqual(payload["error_code"], error_code)

    # -- replay after a possible earlier commit -----------------------------

    def test_update_crash_after_commit_recovers_committed_without_rewrite(self) -> None:
        operation_id = "op-caldav-update-hard-crash"
        self.seed_and_crash("update", operation_id)

        payload = self.payload_of(self.run_worker("update", "recover", operation_id))

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

    def test_update_crash_then_replay_read_failure_is_not_a_confirmed_failure(
        self,
    ) -> None:
        operation_id = "op-caldav-update-replay-read-fails"
        self.seed_and_crash("update", operation_id)

        payload = self.payload_of(
            self.run_worker("update", "recover", operation_id, "get-fails")
        )

        self.assert_unproven(payload, "pre_read_failed_after_possible_send")
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

    def test_update_crash_then_human_edit_is_not_a_fresh_conflict(self) -> None:
        operation_id = "op-caldav-update-edit-after-commit"
        self.seed_and_crash("update", operation_id)
        provider_human_edit(self.provider_db, keep_marker=False)

        payload = self.payload_of(self.run_worker("update", "recover", operation_id))

        self.assert_unproven(payload, "version_conflict_after_possible_send")
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

    def test_update_crash_then_marker_preserving_edit_is_still_committed(self) -> None:
        operation_id = "op-caldav-update-edit-keeps-marker"
        self.seed_and_crash("update", operation_id)
        provider_human_edit(self.provider_db, keep_marker=True)

        payload = self.payload_of(self.run_worker("update", "recover", operation_id))

        self.assertEqual(payload["provider_status"], "committed")
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

    def test_update_crash_then_deletion_is_not_a_confirmed_non_commit(self) -> None:
        operation_id = "op-caldav-update-deleted-after-commit"
        self.seed_and_crash("update", operation_id)
        provider_delete(self.provider_db)

        payload = self.payload_of(self.run_worker("update", "recover", operation_id))

        self.assert_unproven(payload, "event_absent_cause_unknown")
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

    def test_update_crash_then_provider_without_capability_is_not_a_confirmed_failure(
        self,
    ) -> None:
        operation_id = "op-caldav-update-replay-no-capability"
        self.seed_and_crash("update", operation_id)

        payload = self.payload_of(
            self.run_worker("update", "recover", operation_id, "no-capability")
        )

        self.assert_unproven(payload, "provider_not_recoverable_after_possible_send")
        self.assertEqual(call_counts(self.provider_db).get("put"), 1)

    def test_cancel_crash_after_commit_knows_absence_but_not_its_cause(self) -> None:
        operation_id = "op-caldav-cancel-hard-crash"
        self.seed_and_crash("cancel", operation_id)

        payload = self.payload_of(self.run_worker("cancel", "recover", operation_id))

        # The goal state (event absent) is known; whether Ada's DELETE caused
        # it is not. No second DELETE, and no confirmed non-commit.
        self.assert_unproven(payload, "event_absent_cause_unknown")
        self.assertEqual(call_counts(self.provider_db).get("delete"), 1)
        self.assertIsNone(stored_resource(self.provider_db))

    def test_cancel_crash_then_replay_read_failure_is_not_a_confirmed_failure(
        self,
    ) -> None:
        operation_id = "op-caldav-cancel-replay-read-fails"
        self.seed_and_crash("cancel", operation_id)

        payload = self.payload_of(
            self.run_worker("cancel", "recover", operation_id, "get-fails")
        )

        self.assert_unproven(payload, "pre_read_failed_after_possible_send")
        self.assertEqual(call_counts(self.provider_db).get("delete"), 1)

    # -- genuinely fresh requests keep their definite outcomes --------------

    def test_fresh_stale_update_and_cancel_report_a_normal_conflict(self) -> None:
        for kind in ("update", "cancel"):
            with self.subTest(kind):
                self.tearDown()
                self.setUp()
                operation_id = f"op-caldav-{kind}-fresh-stale"
                self.assertEqual(self.run_worker(kind, "seed", operation_id).returncode, 0)
                provider_human_edit(self.provider_db, keep_marker=False)

                payload = self.payload_of(self.run_worker(kind, "run", operation_id))

                self.assertEqual(payload["provider_status"], "failed")
                self.assertEqual(payload["business_status"], "failed")
                self.assertEqual(payload["error_code"], "version_conflict")
                self.assertEqual(call_counts(self.provider_db).get("put"), None)
                self.assertEqual(call_counts(self.provider_db).get("delete"), None)

    def test_fresh_pre_existing_absence_is_a_confirmed_non_effect(self) -> None:
        for kind in ("update", "cancel"):
            with self.subTest(kind):
                self.tearDown()
                self.setUp()
                operation_id = f"op-caldav-{kind}-fresh-absent"
                self.assertEqual(self.run_worker(kind, "seed", operation_id).returncode, 0)
                provider_delete(self.provider_db)

                payload = self.payload_of(self.run_worker(kind, "run", operation_id))

                self.assertEqual(payload["provider_status"], "failed")
                self.assertEqual(payload["error_code"], "event_absent")
                self.assertEqual(call_counts(self.provider_db).get("put"), None)
                self.assertEqual(call_counts(self.provider_db).get("delete"), None)


if __name__ == "__main__":
    unittest.main()
