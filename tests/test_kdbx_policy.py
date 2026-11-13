"""Synthetic-only security-policy regressions for the experimental KDBX reader."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ada.adapters.kdbx_secrets import (
    KdbxSecrets,
    SecretVaultError,
    _validate_kdf_header,
)

try:
    from kdbxtool import Database
    from kdbxtool.security import KdfType
except ImportError:
    Database = None
    KdfType = None


@unittest.skipIf(Database is None, "optional kdbxtool research extra not installed")
class KdbxPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        assert Database is not None
        self.header = Database.create(password="synthetic-only-master")._header
        assert self.header is not None

    def test_default_kdbx4_argon2_allowed(self) -> None:
        _validate_kdf_header(self.header.to_bytes())

    def test_legacy_aes_kdf_and_weak_argon2_rejected(self) -> None:
        assert KdfType is not None
        cases = [
            replace(
                self.header, kdf_type=KdfType.AES_KDF, aes_kdf_rounds=1
            ),
            replace(self.header, argon2_memory_kib=16 * 1024),
            replace(self.header, argon2_iterations=1),
            replace(self.header, argon2_parallelism=0),
        ]
        for header in cases:
            with self.subTest(kdf=header.kdf_type, mem=header.argon2_memory_kib):
                with self.assertRaisesRegex(SecretVaultError, "KDF policy rejected"):
                    _validate_kdf_header(header.to_bytes())

    def test_excessive_argon2_cost_rejected_before_derivation(self) -> None:
        cases = [
            replace(self.header, argon2_memory_kib=1024 * 1024),
            replace(self.header, argon2_iterations=1000),
            replace(self.header, argon2_parallelism=256),
        ]
        for header in cases:
            with self.subTest(header=header.argon2_memory_kib):
                with self.assertRaisesRegex(SecretVaultError, "KDF policy rejected"):
                    _validate_kdf_header(header.to_bytes())

    def test_garbage_file_rejected_without_parser_details(self) -> None:
        with self.assertRaisesRegex(SecretVaultError, "KDF header is invalid") as caught:
            _validate_kdf_header(b"not a vault")
        self.assertNotIn("signature", str(caught.exception))

    def test_weak_header_never_reaches_password_derivation(self) -> None:
        assert Database is not None
        with TemporaryDirectory() as root:
            directory = Path(root) / "secrets"
            directory.mkdir()
            path = directory / "ada.kdbx"
            weak = replace(self.header, argon2_iterations=1)
            path.write_bytes(weak.to_bytes())
            path.chmod(0o600)

            vault = KdbxSecrets(root)
            with (
                patch("ada.adapters.kdbx_secrets._require_protected_credential_process"),
                patch.object(Database, "open_bytes") as decrypt,
            ):
                with self.assertRaisesRegex(SecretVaultError, "KDF policy rejected"):
                    vault.unlock("synthetic-only-master")
                decrypt.assert_not_called()
            self.assertFalse(vault.unlocked)


@unittest.skipUnless(sys.platform == "linux", "Linux prctl is required")
class ProcessHardeningTests(unittest.TestCase):
    def test_same_uid_sibling_cannot_open_protected_process_memory(self) -> None:
        # Target and reader are sibling subprocesses with the same UID.
        # No real secrets or memory bytes are inspected by this test.
        target_program = (
            "import os, sys; "
            "from ada.adapters.kdbx_secrets import protect_credential_process; "
            "protect_credential_process(); print(os.getpid(), flush=True); "
            "sys.stdin.readline()"
        )
        target = subprocess.Popen(
            [sys.executable, "-u", "-c", target_program],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert target.stdout is not None
            pid = target.stdout.readline().strip()
            self.assertTrue(pid.isdigit(), "protected process did not start")
            sibling_program = """
import sys
from pathlib import Path

path = Path("/proc") / sys.argv[1] / "mem"
try:
    with path.open("rb"):
        sys.exit(3)  # Unexpected access to a protected process.
except PermissionError:
    sys.exit(0)
except OSError:
    sys.exit(2)  # Unrelated process/procfs failure.
"""
            result = subprocess.run(
                [sys.executable, "-c", sibling_program, pid],
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            target.terminate()
            target.communicate(timeout=10)

    def test_linux_kernel_reports_not_dumpable_in_fresh_process(self) -> None:
        # Never alter the unittest runner's own dumpable flag.
        command = (
            "from ada.adapters.kdbx_secrets import ("
            "protect_credential_process, _prctl); "
            "protect_credential_process(); assert _prctl(3) == 0"
        )
        result = subprocess.run(
            [sys.executable, "-c", command],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
