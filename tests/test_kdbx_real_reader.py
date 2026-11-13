"""Opt-in KDBX crypto round-trip: runs only if the optional PoC reader exists."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ada.adapters.kdbx_secrets import KdbxSecrets, SecretVaultError

try:
    from kdbxtool import Database
except ImportError:
    Database = None


@unittest.skipIf(Database is None, "optional experimental kdbxtool not installed")
class KdbxRealReaderTests(unittest.TestCase):
    def test_synthetic_kdbx4_unlock_then_lock(self) -> None:
        assert Database is not None
        with TemporaryDirectory() as memory_root:
            secrets = Path(memory_root) / "secrets"
            secrets.mkdir()
            path = secrets / "ada.kdbx"

            database = Database.create(
                password="synthetic-master-not-a-real-credential",
                database_name="Ada test",
            )
            database.root_group.create_entry(
                title="ionos/calendar",
                username="synthetic@example.invalid",
                password="synthetic-only-password",
            )
            database.save(path)
            path.chmod(0o600)
            database.zeroize_credentials()

            vault = KdbxSecrets(
                memory_root, allowed_entries=frozenset({"ionos/calendar"})
            )
            with self.assertRaises(SecretVaultError):
                vault.unlock("incorrect")
            with vault:
                vault.unlock("synthetic-master-not-a-real-credential")
                self.assertEqual(vault.password("ionos/calendar"), "synthetic-only-password")
            self.assertFalse(vault.unlocked)
            with self.assertRaisesRegex(SecretVaultError, "locked"):
                vault.password("ionos/calendar")


if __name__ == "__main__":
    unittest.main()
