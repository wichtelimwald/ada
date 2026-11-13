from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import subprocess
import sys
import unittest
from unittest.mock import patch

from ada.adapters.file_memory import FileMemoryStore
from ada.adapters.kdbx_secrets import KdbxSecrets, SecretVaultError


class FakeDatabase:
    instances: list[FakeDatabase] = []

    def __init__(self) -> None:
        self.zeroized = False
        self.entries = [
            SimpleNamespace(title="ionos/calendar", password="synthetic-password")
        ]
        self.__class__.instances.append(self)

    @classmethod
    def open(cls, path: Path, password: str) -> FakeDatabase:
        if password != "test-master":
            raise ValueError("sensitive upstream diagnostic")
        return cls()

    def find_entries(self, *, title: str) -> list:
        return [entry for entry in self.entries if entry.title == title]

    def zeroize_credentials(self) -> None:
        self.zeroized = True


class KdbxSecretsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "secrets").mkdir()
        self.vault_path = root / "secrets" / "ada.kdbx"
        self.vault_path.write_bytes(b"synthetic-not-real-kdbx")
        self.vault_path.chmod(0o600)
        self.reader = KdbxSecrets(
            root, allowed_entries=frozenset({"ionos/calendar"})
        )
        self.patcher = patch.dict(
            sys.modules, {"kdbxtool": SimpleNamespace(Database=FakeDatabase)}
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_locked_by_default_and_deny_unknown_reference(self) -> None:
        self.assertFalse(self.reader.unlocked)
        with self.assertRaisesRegex(SecretVaultError, "not authorized"):
            self.reader.password("untis/other")
        with self.assertRaisesRegex(SecretVaultError, "locked"):
            self.reader.password("ionos/calendar")

    def test_unlock_lookup_and_lock(self) -> None:
        with self.reader as reader:
            reader.unlock("test-master")
            self.assertEqual(
                reader.password("ionos/calendar"), "synthetic-password"
            )
            with self.assertRaisesRegex(SecretVaultError, "not authorized"):
                reader.password("untis/other")
            db = FakeDatabase.instances[-1]
        self.assertFalse(self.reader.unlocked)
        self.assertTrue(db.zeroized)
        with self.assertRaisesRegex(SecretVaultError, "locked"):
            self.reader.password("ionos/calendar")

    def test_wrong_passphrase_leaks_no_library_error(self) -> None:
        with self.assertRaises(SecretVaultError) as caught:
            self.reader.unlock("incorrect")
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertFalse(self.reader.unlocked)

    def test_duplicate_and_missing_entries_fail_closed(self) -> None:
        self.reader.unlock("test-master")
        db = FakeDatabase.instances[-1]
        db.entries.append(
            SimpleNamespace(title="ionos/calendar", password="duplicate")
        )
        with self.assertRaisesRegex(SecretVaultError, "ambiguous"):
            self.reader.password("ionos/calendar")
        db.entries.clear()
        with self.assertRaisesRegex(SecretVaultError, "missing"):
            self.reader.password("ionos/calendar")

    def test_rejects_symlink_permissions_and_oversized_file(self) -> None:
        with TemporaryDirectory() as outside:
            target = Path(outside) / "outside.kdbx"
            target.write_bytes(b"not-kdbx")
            target.chmod(0o600)
            self.vault_path.unlink()
            self.vault_path.symlink_to(target)
            with self.assertRaisesRegex(SecretVaultError, "symlinks"):
                self.reader.unlock("test-master")
            self.vault_path.unlink()
        self.vault_path.write_bytes(b"not-kdbx")
        self.vault_path.chmod(0o644)
        with self.assertRaisesRegex(SecretVaultError, "owner-only"):
            self.reader.unlock("test-master")
        self.vault_path.chmod(0o600)
        with self.vault_path.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(SecretVaultError, "bounded"):
            self.reader.unlock("test-master")

    def test_missing_vault_does_not_get_created(self) -> None:
        self.vault_path.unlink()
        with self.assertRaisesRegex(SecretVaultError, "not accessible"):
            self.reader.unlock("test-master")
        self.assertFalse(self.vault_path.exists())

    def test_cli_unlocks_only_in_its_own_process(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO
        from ada.cli import _secrets_check

        output = StringIO()
        with (
            patch("ada.cli.sys.stdin.isatty", return_value=True),
            patch("getpass.getpass", return_value="test-master"),
            redirect_stdout(output),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 0)
        self.assertIn("now locked again", output.getvalue())
        self.assertNotIn("synthetic-password", output.getvalue())
        self.assertNotIn("test-master", output.getvalue())

    def test_cli_without_tty_never_asks_for_passphrase(self) -> None:
        from contextlib import redirect_stderr
        from io import StringIO
        from ada.cli import _secrets_check

        output = StringIO()
        with (
            patch("ada.cli.sys.stdin.isatty", return_value=False),
            patch("getpass.getpass") as ask,
            redirect_stderr(output),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 2)
        ask.assert_not_called()
        self.assertIn("interactive terminal", output.getvalue())


    def test_memory_git_does_not_stage_vault_even_with_add_all(self) -> None:
        with TemporaryDirectory() as root:
            FileMemoryStore(root)
            directory = Path(root) / "secrets"
            directory.mkdir()
            vault = directory / "ada.kdbx"
            vault.write_bytes(b"synthetic-ciphertext")
            vault.chmod(0o600)

            subprocess.run(
                ["git", "-C", root, "add", "-A"],
                check=True, capture_output=True,
            )
            tracked = subprocess.run(
                ["git", "-C", root, "ls-files", "-z", "--", "secrets"],
                check=True, capture_output=True,
            ).stdout
            self.assertEqual(tracked, b"")

            # Explicit force-add bypasses ignore; Ada refuses the tainted repo.
            subprocess.run(
                ["git", "-C", root, "add", "-f", "secrets/ada.kdbx"],
                check=True, capture_output=True,
            )
            with self.assertRaisesRegex(Exception, "already tracked"):
                FileMemoryStore(root)


if __name__ == "__main__":
    unittest.main()
