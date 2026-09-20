from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ledger import Ledger
from provider import FakeProvider
from recovery import recover_one


class LedgerRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ledger_path = root / "ledger.sqlite3"
        self.provider_path = root / "provider.sqlite3"
        self.ledger = Ledger(self.ledger_path)
        self.provider = FakeProvider(self.provider_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def new_authorized(self, operation_id: str = "op-1") -> None:
        self.ledger.create(operation_id, "calendar.create", "fake-calendar")
        self.ledger.transition(operation_id, "proposed", "authorized")

    def test_provider_commit_then_hard_crash_recovers_without_duplicate(self) -> None:
        self.new_authorized()

        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("crash_worker.py")),
                str(self.ledger_path),
                str(self.provider_path),
                "op-1",
            ],
            check=False,
        )
        self.assertEqual(proc.returncode, 17)

        restarted_ledger = Ledger(self.ledger_path)
        restarted_provider = FakeProvider(self.provider_path)

        self.assertEqual(restarted_ledger.get("op-1").state, "executing")
        self.assertEqual(restarted_provider.effect_count("op-1"), 1)

        result = recover_one(restarted_ledger, restarted_provider, "op-1")

        self.assertEqual(result, "committed")
        self.assertEqual(restarted_ledger.get("op-1").state, "committed")
        self.assertEqual(restarted_provider.effect_count("op-1"), 1)

    def test_denied_operation_causes_zero_provider_writes(self) -> None:
        self.ledger.create("op-denied", "calendar.create", "fake-calendar")
        self.ledger.transition("op-denied", "proposed", "denied")

        self.assertEqual(self.ledger.get("op-denied").state, "denied")
        self.assertEqual(self.provider.effect_count("op-denied"), 0)

    def test_illegal_transition_is_rejected(self) -> None:
        self.ledger.create("op-illegal", "calendar.create", "fake-calendar")

        with self.assertRaises(ValueError):
            self.ledger.transition("op-illegal", "proposed", "committed")

    def test_compare_and_set_prevents_double_claim(self) -> None:
        self.new_authorized("op-claim")

        self.ledger.transition("op-claim", "authorized", "executing")

        with self.assertRaises(RuntimeError):
            self.ledger.transition("op-claim", "authorized", "executing")

    def test_unknown_provider_outcome_without_reconciliation_is_not_retried(self) -> None:
        self.new_authorized("op-ambiguous")
        self.ledger.transition("op-ambiguous", "authorized", "executing")

        no_reconcile = FakeProvider(
            self.provider_path,
            supports_reconciliation=False,
        )

        result = recover_one(self.ledger, no_reconcile, "op-ambiguous")

        self.assertEqual(result, "ambiguous")
        self.assertEqual(self.ledger.get("op-ambiguous").state, "ambiguous")
        self.assertEqual(no_reconcile.effect_count("op-ambiguous"), 0)


if __name__ == "__main__":
    unittest.main()
