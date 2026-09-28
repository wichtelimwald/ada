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


def _load_probe():
    spec = importlib.util.spec_from_file_location("ada_mvp30_s2_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load MVP-30 S2 probe module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MVP30S2ProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = _load_probe()

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
