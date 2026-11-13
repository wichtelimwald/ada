from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx2

from ada.adapters.caldav.development_config import (
    IONOSDevelopmentConfigurationError,
    build_development_ionos_adapter,
    load_ionos_development_settings,
    read_ionos_keychain_password,
)
from ada.ports.calendar import CalendarAccessMode, CalendarAudience


GOOD = """version = 1
mailbox = "ada@example.invalid"
base_url = "https://dav.mailbusiness.ionos.de"

[[calendar]]
id = "family"
collection = "/caldav/synthetic-family/"
audience = "family"
access = "write"

[[calendar]]
id = "person_a"
collection = "/caldav/synthetic-person/"
audience = "person"
access = "read"
"""


class IONOSDevelopmentConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "calendar.toml"
        self.put(GOOD)

    def put(self, contents: str) -> None:
        self.path.write_text(contents, encoding="utf-8")
        self.path.chmod(0o600)

    def test_nonsecret_settings_are_parsed_and_scoped(self) -> None:
        settings = load_ionos_development_settings(self.path)
        self.assertEqual(settings.mailbox, "ada@example.invalid")
        self.assertEqual(settings.base_url, "https://dav.mailbusiness.ionos.de")
        self.assertEqual([r.calendar_id for r in settings.calendars],
                         ["family", "person_a"])
        self.assertEqual(settings.calendars[0].access_mode, CalendarAccessMode.WRITE)
        self.assertEqual(settings.calendars[0].audience, CalendarAudience.FAMILY)
        self.assertEqual(settings.calendars[1].access_mode, CalendarAccessMode.READ)
        self.assertNotIn("ada@example.invalid", repr(settings))
        self.assertNotIn("synthetic-family", repr(settings))

    def test_private_file_permissions_are_required(self) -> None:
        self.path.chmod(0o644)
        with self.assertRaises(IONOSDevelopmentConfigurationError):
            load_ionos_development_settings(self.path)

    def test_symlink_is_refused(self) -> None:
        link = Path(self.tmp.name) / "link.toml"
        link.symlink_to(self.path)
        with self.assertRaises(IONOSDevelopmentConfigurationError):
            load_ionos_development_settings(link)

    def test_unknown_keys_and_secret_field_are_rejected(self) -> None:
        for extra in ('password = "do-not-use"\n', 'token = "do-not-use"\n'):
            with self.subTest(extra=extra):
                self.put(GOOD.replace('base_url = ', extra + 'base_url = '))
                with self.assertRaises(IONOSDevelopmentConfigurationError):
                    load_ionos_development_settings(self.path)

    def test_wrong_origin_refused_before_password_access(self) -> None:
        for candidate_url in (
            "http://dav.mailbusiness.ionos.de",
            "https://evil.invalid",
            "https://dav.mailbusiness.ionos.de.evil.invalid",
            "https://user@dav.mailbusiness.ionos.de",
            "https://dav.mailbusiness.ionos.de:443",
            "https://dav.mailbusiness.ionos.de/elsewhere",
        ):
            with self.subTest(url=candidate_url):
                self.put(GOOD.replace(
                    "https://dav.mailbusiness.ionos.de", candidate_url
                ))
                requested: list[str] = []
                with self.assertRaises(IONOSDevelopmentConfigurationError):
                    build_development_ionos_adapter(
                        self.path,
                        password_reader=lambda name: requested.append(name) or "synthetic",
                    )
                self.assertEqual(requested, [])

    def test_duplicate_or_invalid_calendar_mappings_are_refused(self) -> None:
        for text in (
            GOOD.replace('id = "person_a"', 'id = "family"'),
            GOOD.replace('/caldav/synthetic-person/', 'https://other.invalid/caldav/id'),
            GOOD.replace('/caldav/synthetic-person/', '/not-caldav/id'),
            GOOD.replace('access = "read"', 'access = "admin"'),
            GOOD.replace('audience = "person"', 'audience = "world"'),
        ):
            with self.subTest(case=text[-90:]):
                self.put(text)
                with self.assertRaises(IONOSDevelopmentConfigurationError):
                    load_ionos_development_settings(self.path)

    def test_build_adapter_does_not_contact_network(self) -> None:
        calls: list[httpx2.Request] = []

        def forbidden_request(request: httpx2.Request) -> httpx2.Response:
            calls.append(request)
            raise AssertionError("constructor must not perform network I/O")

        reader_calls: list[str] = []
        adapter = build_development_ionos_adapter(
            self.path,
            password_reader=lambda mailbox: reader_calls.append(mailbox) or "synthetic",
            transport=httpx2.MockTransport(forbidden_request),
        )
        self.addCleanup(adapter.close)
        self.assertEqual(reader_calls, ["ada@example.invalid"])
        self.assertEqual(calls, [])
        self.assertEqual(adapter._base_url, "https://dav.mailbusiness.ionos.de")

    def test_invalid_config_prevents_keychain_read(self) -> None:
        self.path.chmod(0o666)
        reader_calls: list[str] = []
        with self.assertRaises(IONOSDevelopmentConfigurationError):
            build_development_ionos_adapter(
                self.path,
                password_reader=lambda mailbox: reader_calls.append(mailbox) or "synthetic",
            )
        self.assertEqual(reader_calls, [])


class IONOSKeychainTests(unittest.TestCase):
    def test_other_platforms_fail_closed(self) -> None:
        with patch("ada.adapters.caldav.development_config.sys.platform", "linux"):
            with self.assertRaisesRegex(IONOSDevelopmentConfigurationError, "macOS"):
                read_ionos_keychain_password("ada@example.invalid")

    def test_macos_reads_existing_item_without_shell_or_secret_arguments(self) -> None:
        result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"synthetic-pass\n", stderr=b""
        )
        with (
            patch("ada.adapters.caldav.development_config.sys.platform", "darwin"),
            patch("ada.adapters.caldav.development_config.subprocess.run", return_value=result)
            as run,
        ):
            self.assertEqual(
                read_ionos_keychain_password("ada@example.invalid"),
                "synthetic-pass",
            )
        kwargs = run.call_args.kwargs
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ["/usr/bin/security", "find-generic-password",
                                    "-s", "ada-caldav"])
        self.assertEqual(argv[-1], "-w")
        self.assertNotIn("synthetic-pass", repr(argv))
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    def test_failures_do_not_echo_keychain_output(self) -> None:
        outputs = (
            subprocess.CompletedProcess(args=[], returncode=1,
                                        stdout=b"do-not-log", stderr=b"secret"),
            subprocess.CompletedProcess(args=[], returncode=0,
                                        stdout=b"\xff", stderr=b""),
        )
        for fake in outputs:
            with self.subTest(status=fake.returncode), (
                patch("ada.adapters.caldav.development_config.sys.platform", "darwin"),
                patch("ada.adapters.caldav.development_config.subprocess.run",
                      return_value=fake),
            ):
                with self.assertRaises(IONOSDevelopmentConfigurationError) as cm:
                    read_ionos_keychain_password("ada@example.invalid")
                self.assertNotIn("do-not-log", str(cm.exception))
                self.assertNotIn("secret", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
