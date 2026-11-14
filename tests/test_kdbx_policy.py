"""Synthetic-only security-policy regressions for the experimental KDBX reader."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
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


class AdaRuntimeHashCaptureTests(unittest.TestCase):
    def test_capture_accepts_reviewed_kdbx_pins(self) -> None:
        from scripts.capture_ada_runtime_hashes import (
            PROJECT_ROOT,
            _name,
            _pins_from_lock,
        )

        self.assertEqual(_name("argon2_cffi.bindings"), "argon2-cffi-bindings")
        pins = _pins_from_lock(
            PROJECT_ROOT / "requirements/kdbx-py314-linux-aarch64.txt"
        )
        self.assertEqual(len(pins), 7)
        self.assertEqual(pins["kdbxtool"][0], "0.1.7")


class CredentialRuntimeInventoryTests(unittest.TestCase):
    def test_runtime_lock_parser_requires_setuptools_and_kdbx(self) -> None:
        from scripts.check_credential_runtime_lock import locked_versions

        with TemporaryDirectory() as root:
            lock = Path(root) / "lock.txt"
            lock.write_text(
                "setuptools==80.9.0 --hash=sha256:" + "a" * 64 + "\n"
                "kdbxtool==0.1.7 --hash=sha256:" + "b" * 64 + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                locked_versions(lock),
                {"setuptools": "80.9.0", "kdbxtool": "0.1.7"},
            )
            lock.write_text("kdbxtool==0.1.7 --hash=sha256:" + "b" * 64 + "\n")
            with self.assertRaisesRegex(ValueError, "Missing build backend"):
                locked_versions(lock)


class CredentialDockerLauncherTests(unittest.TestCase):
    def test_launchers_rely_on_private_pid_default_and_keep_sandbox(self) -> None:
        root = Path(__file__).resolve().parents[1] / "scripts"
        for filename in (
            "smoke_credential_runtime.sh",
            "run_ada_credentials.sh",
        ):
            with self.subTest(script=filename):
                script = root / filename
                source = script.read_text(encoding="utf-8")
                active = "\n".join(
                    line for line in source.splitlines()
                    if not line.lstrip().startswith("#")
                )
                # Docker's default is a private PID namespace. --pid private
                # is INVALID and must not recur in the production launcher.
                self.assertNotRegex(active, r"--pid(?:\s|=)")
                for required in (
                    "--network none",
                    "--read-only",
                    "--cap-drop ALL",
                    "--security-opt no-new-privileges",
                    "--memory 1g --memory-swap 1g",
                    "--pull never",
                ):
                    self.assertIn(required, active)
                checked = subprocess.run(
                    ["sh", "-n", str(script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)


class CredentialRuntimePinnedGraphTests(unittest.TestCase):
    def test_full_hash_lock_covers_all_adopted_packages(self) -> None:
        import tomllib
        from scripts.check_credential_runtime_lock import locked_versions

        root = Path(__file__).resolve().parents[1]
        full = locked_versions(
            root / "requirements/ada-runtime-py314-linux-aarch64.txt"
        )
        kdbx = {}
        for line in (
            root / "requirements/kdbx-py314-linux-aarch64.txt"
        ).read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            match = re.fullmatch(
                r"([a-z0-9-]+)==([0-9.]+) --hash=sha256:([a-f0-9]{64})",
                line,
            )
            self.assertIsNotNone(match)
            assert match is not None
            kdbx[match.group(1)] = match.group(2)
        for name, version in kdbx.items():
            self.assertEqual(full.get(name), version)

        pyproject = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
        # First-level packages and the build backend must be present in
        # the full transitive graph, independent of the lock file count.
        for item in (
            *pyproject["project"]["dependencies"],
            *pyproject["project"]["optional-dependencies"]["secrets-poc"],
            *pyproject["build-system"]["requires"],
        ):
            name = re.split(r"[<>=\\[;! ]", item, maxsplit=1)[0]
            name = re.sub(r"[-_.]+", "-", name).lower()
            self.assertIn(name, full, f"Unhashed dependency: {item}")

        self.assertGreaterEqual(len(full), 49)


class KdbxWheelLockTests(unittest.TestCase):
    def test_committed_lock_matches_expected_versions_and_sha256(self) -> None:
        from scripts.capture_kdbx_wheel_hashes import PINS

        manifest = (
            Path(__file__).resolve().parents[1]
            / "requirements"
            / "kdbx-py314-linux-aarch64.txt"
        )
        lines = [
            line for line in manifest.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        hashes: dict[str, str] = {}
        versions: dict[str, str] = {}
        for line in lines:
            match = re.fullmatch(
                r"([a-z0-9-]+)==([0-9.]+) --hash=sha256:([a-f0-9]{64})",
                line,
            )
            self.assertIsNotNone(match, f"Invalid KDBX hash lock entry: {line}")
            assert match is not None
            name, version, digest = match.groups()
            self.assertNotIn(name, hashes)
            versions[name] = version
            hashes[name] = digest
        self.assertEqual(versions, PINS)
        self.assertEqual(len(hashes), 7)


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

    def test_kee_passxc_autocalibrated_cost_is_accepted(self) -> None:
        # KeePassXC 2.8.0 targets ~1 second, not a fixed 10 rounds.
        # This header-only test does NOT derive a key or claim speed on all hosts.
        assert KdfType is not None
        for version in (KdfType.ARGON2ID, KdfType.ARGON2D):
            with self.subTest(version=version):
                header = replace(
                    self.header,
                    kdf_type=version,
                    argon2_memory_kib=64 * 1024,
                    argon2_iterations=51,
                    argon2_parallelism=4,
                )
                _validate_kdf_header(header.to_bytes())

    def test_strict_runtime_rejects_cheap_kdf_but_accepts_calibrated(self) -> None:
        # Strict credentials require at least 2048 MiB-rounds; a 64 MiB
        # KeePassXC auto-calibrated 51-round vault still passes.
        with patch.dict(
            "os.environ", {"ADA_REQUIRE_ISOLATED_CREDENTIALS": "1"}
        ):
            for header in (
                replace(self.header, argon2_memory_kib=64 * 1024, argon2_iterations=3),
                replace(self.header, argon2_memory_kib=256 * 1024, argon2_iterations=3),
            ):
                with self.subTest(mem=header.argon2_memory_kib):
                    with self.assertRaisesRegex(SecretVaultError, "KDF policy rejected"):
                        _validate_kdf_header(header.to_bytes())
            calibrated = replace(
                self.header,
                argon2_memory_kib=64 * 1024,
                argon2_iterations=51,
                argon2_parallelism=4,
            )
            _validate_kdf_header(calibrated.to_bytes())

    def test_excessive_argon2_cost_rejected_before_derivation(self) -> None:
        cases = [
            replace(self.header, argon2_memory_kib=1024 * 1024),
            replace(self.header, argon2_iterations=1000),
            replace(self.header, argon2_parallelism=256),
            replace(
                self.header,
                argon2_memory_kib=256 * 1024,
                argon2_iterations=33,
            ),
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


@unittest.skipUnless(sys.platform == "linux", "Linux procfs is required")
class CredentialNamespaceGateTests(unittest.TestCase):
    def test_strict_mode_rejects_non_pid_one(self) -> None:
        from ada.adapters.kdbx_secrets import _require_isolated_credential_namespace

        with patch("ada.adapters.kdbx_secrets.os.getpid", return_value=77):
            with self.assertRaisesRegex(SecretVaultError, "namespace is not isolated"):
                _require_isolated_credential_namespace()

    def test_strict_mode_rejects_co_resident_process(self) -> None:
        from ada.adapters.kdbx_secrets import _require_isolated_credential_namespace

        with (
            patch("ada.adapters.kdbx_secrets.os.getpid", return_value=1),
            patch("ada.adapters.kdbx_secrets.os.listdir", return_value=["1", "2", "self"]),
        ):
            with self.assertRaisesRegex(SecretVaultError, "namespace is not isolated"):
                _require_isolated_credential_namespace()

    def test_strict_mode_accepts_pid_one_alone(self) -> None:
        from ada.adapters.kdbx_secrets import _require_isolated_credential_namespace

        with (
            patch("ada.adapters.kdbx_secrets.os.getpid", return_value=1),
            patch("ada.adapters.kdbx_secrets.os.listdir", return_value=["1", "self"]),
        ):
            _require_isolated_credential_namespace()

    def test_strict_runtime_enforces_python_and_cgroup_limits(self) -> None:
        from ada.adapters.kdbx_secrets import _require_strict_credential_runtime

        with (
            patch("ada.adapters.kdbx_secrets._require_isolated_credential_namespace"),
            patch("ada.adapters.kdbx_secrets.sys.flags", SimpleNamespace(
                isolated=1, no_user_site=1
            )),
            patch("ada.adapters.kdbx_secrets.os.statvfs",
                  return_value=SimpleNamespace(f_flag=os.ST_RDONLY)),
        ):
            with patch("ada.adapters.kdbx_secrets.Path.read_text",
                       side_effect=["1073741824", "0"]):
                _require_strict_credential_runtime()
            for memory, swap in (("max", "0"), ("1073741824", "max"),
                                 ("2147483648", "0")):
                with self.subTest(memory=memory, swap=swap):
                    with patch("ada.adapters.kdbx_secrets.Path.read_text",
                               side_effect=[memory, swap]):
                        with self.assertRaisesRegex(SecretVaultError, "limits not enforced"):
                            _require_strict_credential_runtime()

    def test_strict_runtime_rejects_normal_python_invocation(self) -> None:
        from ada.adapters.kdbx_secrets import _require_strict_credential_runtime

        with (
            patch("ada.adapters.kdbx_secrets._require_isolated_credential_namespace"),
            patch("ada.adapters.kdbx_secrets.sys.flags", SimpleNamespace(
                isolated=0, no_user_site=0
            )),
        ):
            with self.assertRaisesRegex(SecretVaultError, "Python runtime is not isolated"):
                _require_strict_credential_runtime()

    def test_adapter_enforces_namespace_gate_when_enabled(self) -> None:
        from unittest.mock import patch as mock_patch

        with (
            mock_patch.dict("os.environ", {"ADA_REQUIRE_ISOLATED_CREDENTIALS": "1"}),
            mock_patch("ada.adapters.kdbx_secrets._require_protected_credential_process"),
            mock_patch(
                "ada.adapters.kdbx_secrets._require_isolated_credential_namespace",
                side_effect=SecretVaultError("Ada credential PID namespace is not isolated"),
            ),
        ):
            with self.assertRaisesRegex(SecretVaultError, "namespace is not isolated"):
                KdbxSecrets("/synthetic-only").unlock("synthetic-master")


@unittest.skipUnless(sys.platform == "linux", "Linux prctl is required")
class ProcessHardeningTests(unittest.TestCase):
    def test_late_same_uid_sibling_cannot_open_protected_process_memory(self) -> None:
        # Target protects itself before the sibling attempts to open /proc.
        # This intentionally tests only LATE openers. A sibling that opened
        # /proc/<pid>/mem before prctl keeps access (PR #59 review B1).
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
