from __future__ import annotations

import importlib.util
from pathlib import Path
import plistlib
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = (
    REPO_ROOT / "research" / "memory" / "mvp-30-s2" / "probe_encrypted_vault.py"
)
PROBE_B_PATH = (
    REPO_ROOT / "research" / "memory" / "mvp-30-s2" / "probe_restricted_runtime.py"
)


def _load_probe():
    spec = importlib.util.spec_from_file_location("ada_mvp30_s2_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load MVP-30 S2 probe module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MVP30S2ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.probe = _load_probe()

    def test_hdi_password_keeps_secret_out_of_argv_shape(self) -> None:
        self.assertEqual(self.probe.hdi_password("synthetic"), b"synthetic")

    def test_parse_attached_device_finds_expected_mount(self) -> None:
        mountpoint = Path("/tmp/ada-mvp30-s2-test-mount")
        payload = plistlib.dumps(
            {
                "system-entities": [
                    {
                        "dev-entry": "/dev/disk99s1",
                        "mount-point": str(mountpoint),
                    }
                ]
            }
        )

        self.assertEqual(
            self.probe.parse_attached_device(payload, mountpoint),
            "/dev/disk99s1",
        )

    def test_probe_b_never_bootstraps_sudo_credentials(self) -> None:
        source = PROBE_B_PATH.read_text(encoding="utf-8")

        self.assertNotIn("sudo -v", source)
        self.assertNotIn('shutil.which("sudo")', source)
        self.assertNotIn("[sudo,", source)
        self.assertIn("manual_identity_switch_command", source)

    def test_probe_b_has_no_compiler_dependency(self) -> None:
        source = PROBE_B_PATH.read_text(encoding="utf-8")

        self.assertNotIn("swiftc", source)
        self.assertNotIn("xcrun", source)
        self.assertNotIn("clang", source)
        self.assertIn('SECURITY = Path("/usr/bin/security")', source)
        self.assertIn('"security -i via stdin"', source)

    def test_probe_b_uses_cross_identity_traversable_tmp_root(self) -> None:
        source = PROBE_B_PATH.read_text(encoding="utf-8")

        self.assertIn('tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir="/tmp")', source)
        self.assertNotIn("tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))", source)

    def test_missing_distinct_runtime_user_is_not_treated_as_evidence(self) -> None:
        with mock.patch.object(
            self.probe.pwd,
            "getpwnam",
            side_effect=KeyError("synthetic missing user"),
        ):
            status, readable = self.probe.distinct_user_can_read(
                Path("/tmp/does-not-matter"),
                "synthetic-missing-user",
            )

        self.assertEqual(status, "skipped:runtime-user-not-found")
        self.assertIsNone(readable)


if __name__ == "__main__":
    unittest.main()
