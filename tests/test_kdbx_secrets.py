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
        self.zeroize_calls = 0
        self.entries = [
            SimpleNamespace(title="ionos/calendar", password="synthetic-password")
        ]
        self.__class__.instances.append(self)

    @classmethod
    def open_bytes(cls, data: bytes, password: str) -> FakeDatabase:
        if password != "test-master":
            raise ValueError("sensitive upstream diagnostic")
        return cls()

    def find_entries(self, *, title: str) -> list:
        return [entry for entry in self.entries if entry.title == title]

    def zeroize_credentials(self) -> None:
        self.zeroized = True
        self.zeroize_calls += 1


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
        for target in (
            "ada.adapters.kdbx_secrets._require_protected_credential_process",
            "ada.adapters.kdbx_secrets.protect_credential_process",
            "ada.adapters.kdbx_secrets._validate_kdf_header",
        ):
            mocker = patch(target)
            mocker.start()
            self.addCleanup(mocker.stop)

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
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
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
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: False)),
            patch("getpass.getpass") as ask,
            redirect_stderr(output),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 2)
        ask.assert_not_called()
        self.assertIn("interactive terminal", output.getvalue())


    def test_chat_keeps_vault_unlocked_until_runtime_is_closed(self) -> None:
        from unittest.mock import AsyncMock
        from ada.cli import _chat

        runtime = SimpleNamespace(aclose=AsyncMock())
        during_session: list[bool] = []

        def inspect_session(_runtime: object) -> int:
            during_session.append(FakeDatabase.instances[-1].zeroize_calls)
            return 0

        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch("getpass.getpass", return_value="test-master"),
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch(
                "ada.adapters.local_ollama.build_local_ollama_runtime",
                return_value=runtime,
            ) as build,
            patch("ada.cli._chat_loop", side_effect=inspect_session),
        ):
            result = _chat(
                model="qwen3.5:9b",
                ollama_url="http://localhost:11434/v1",
                unlock_vault=True,
                vault_root=self.temp.name,
            )

        self.assertEqual(result, 0)
        self.assertEqual(during_session, [1])
        self.assertTrue(FakeDatabase.instances[-1].zeroized)
        self.assertEqual(FakeDatabase.instances[-1].zeroize_calls, 2)
        runtime.aclose.assert_awaited_once_with()
        self.assertNotIn("vault", repr(build.call_args).lower())

    def test_chat_failure_still_closes_runtime_then_vault(self) -> None:
        from contextlib import redirect_stderr
        from io import StringIO
        from unittest.mock import AsyncMock
        from ada.cli import _chat

        shutdown_observations: list[bool] = []

        async def close() -> None:
            shutdown_observations.append(
                FakeDatabase.instances[-1].zeroize_calls
            )

        runtime = SimpleNamespace(aclose=AsyncMock(side_effect=close))
        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch("getpass.getpass", return_value="test-master"),
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch(
                "ada.adapters.local_ollama.build_local_ollama_runtime",
                return_value=runtime,
            ),
            patch("ada.cli._chat_loop", side_effect=RuntimeError("synthetic failure")),
            redirect_stderr(StringIO()),
        ):
            result = _chat(
                model="qwen3.5:9b",
                ollama_url="http://localhost:11434/v1",
                unlock_vault=True,
                vault_root=self.temp.name,
            )

        self.assertEqual(result, 1)
        self.assertEqual(shutdown_observations, [1])
        self.assertTrue(FakeDatabase.instances[-1].zeroized)
        runtime.aclose.assert_awaited_once_with()

    def test_unlock_fails_if_terminal_echo_cannot_be_disabled(self) -> None:
        from contextlib import redirect_stderr
        from getpass import GetPassWarning
        from io import StringIO
        from ada.cli import _secrets_check

        output = StringIO()
        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch("getpass.getpass", side_effect=GetPassWarning("echo enabled")),
            redirect_stderr(output),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 2)
        self.assertNotIn("echo enabled", output.getvalue())
        self.assertFalse(self.reader.unlocked)

    def test_prompt_is_protected_before_getpass(self) -> None:
        from ada.cli import _secrets_check

        sequence: list[str] = []
        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch(
                "ada.adapters.kdbx_secrets.protect_credential_process",
                side_effect=lambda: sequence.append("protected"),
            ),
            patch(
                "getpass.getpass",
                side_effect=lambda _prompt: (sequence.append("prompt"), "test-master")[1],
            ),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 0)
        self.assertEqual(sequence, ["protected", "prompt"])

    def test_process_protection_failure_does_not_prompt(self) -> None:
        from contextlib import redirect_stderr
        from io import StringIO
        from ada.cli import _secrets_check

        output = StringIO()
        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch(
                "ada.adapters.kdbx_secrets.protect_credential_process",
                side_effect=SecretVaultError("Ada credential process isolation unavailable"),
            ),
            patch("getpass.getpass") as getpass,
            redirect_stderr(output),
        ):
            self.assertEqual(_secrets_check(self.temp.name), 2)
        getpass.assert_not_called()
        self.assertIn("process isolation unavailable", output.getvalue())

    def test_reader_refuses_unprotected_direct_use(self) -> None:
        with patch(
            "ada.adapters.kdbx_secrets._require_protected_credential_process",
            side_effect=SecretVaultError("Ada credential process isolation unavailable"),
        ):
            with self.assertRaisesRegex(SecretVaultError, "process isolation unavailable"):
                self.reader.unlock("test-master")
        self.assertFalse(self.reader.unlocked)


    def test_chat_cli_vault_opt_in_requires_flag(self) -> None:
        from ada.cli import build_parser

        opts = build_parser().parse_args(
            ["chat", "--unlock-vault", "--vault-root", "/ada-memory"]
        )
        self.assertTrue(opts.unlock_vault)
        self.assertEqual(opts.vault_root, "/ada-memory")
        self.assertFalse(build_parser().parse_args(["chat"]).unlock_vault)

    def test_chat_wrong_password_exits_without_running_agent(self) -> None:
        from contextlib import redirect_stderr
        from io import StringIO
        from ada.cli import _chat

        output = StringIO()
        with (
            patch("ada.cli.sys.stdin", SimpleNamespace(isatty=lambda: True)),
            patch("getpass.getpass", return_value="incorrect"),
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch("ada.adapters.local_ollama.build_local_ollama_runtime") as build,
            patch("ada.cli._chat_loop") as chat_loop,
            redirect_stderr(output),
        ):
            result = _chat(
                model="qwen3.5:9b",
                ollama_url="http://localhost:11434/v1",
                unlock_vault=True,
                vault_root=self.temp.name,
            )

        self.assertEqual(result, 2)
        build.assert_not_called()
        chat_loop.assert_not_called()
        self.assertNotIn("sensitive upstream", output.getvalue())
        self.assertNotIn("incorrect", output.getvalue())

    def test_chat_uses_no_vault_when_opt_in_absent(self) -> None:
        from unittest.mock import AsyncMock
        from ada.cli import _chat

        runtime = SimpleNamespace(aclose=AsyncMock())
        with (
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch(
                "ada.adapters.local_ollama.build_local_ollama_runtime",
                return_value=runtime,
            ),
            patch("ada.cli._chat_loop", return_value=0),
            patch("getpass.getpass") as ask,
        ):
            self.assertEqual(
                _chat(model="qwen3.5:9b", ollama_url="http://localhost:11434/v1"),
                0,
            )
        ask.assert_not_called()
        runtime.aclose.assert_awaited_once_with()

    def test_chat_without_vault_path_fails_before_prompt(self) -> None:
        from contextlib import redirect_stderr
        from io import StringIO
        from ada.cli import _chat

        output = StringIO()
        with (
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch("ada.adapters.local_ollama.build_local_ollama_runtime") as build,
            patch("getpass.getpass") as ask,
            redirect_stderr(output),
        ):
            result = _chat(
                model="qwen3.5:9b",
                ollama_url="http://localhost:11434/v1",
                unlock_vault=True,
            )
        self.assertEqual(result, 2)
        self.assertIn("requires", output.getvalue())
        ask.assert_not_called()
        build.assert_not_called()

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
