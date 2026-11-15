"""MVP-60 S6: trusted configuration -> KDBX reference -> read-only CalDAV."""

from __future__ import annotations

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx2

from ada.application.calendar_connection import (
    CalendarConnectionConfig,
    CalendarConnectionConfigurationError,
    load_connection_config,
    probe_connection,
)
from ada.cli import _calendar_probe, build_parser
from ada.adapters.caldav.dav_client import CalDAVConfigurationError, CalDAVProtocolError
from caldav_test_support import (
    BASE_URL,
    FAMILY_PATH,
    READ_ONLY_PATH,
    build_fake_server,
    default_family_ref,
    default_read_only_ref,
)


def _payload() -> dict:
    return {
        "provider": "ionos",
        "base_url": BASE_URL,
        "username": "ada@example.invalid",
        "password_ref": "ionos/calendar",
        "calendars": [
            {
                "id": "family",
                "collection": FAMILY_PATH,
                "audience": "family",
                "mode": "write",
            },
            {
                "id": "guardian-a",
                "collection": READ_ONLY_PATH,
                "audience": "person",
                "mode": "read",
            },
        ],
    }


def _write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)


class CalendarConnectionConfigTests(unittest.TestCase):
    def test_config_maps_only_explicit_nonsecret_fields(self) -> None:
        with TemporaryDirectory() as folder:
            file = Path(folder) / "pilot.json"
            _write_config(file, _payload())
            config = load_connection_config(file)
        self.assertEqual(config.base_url, BASE_URL)
        self.assertEqual(config.password_ref, "ionos/calendar")
        self.assertEqual(len(config.calendars), 2)
        self.assertEqual(config.calendars[0], default_family_ref())
        self.assertEqual(config.calendars[1], default_read_only_ref())
        self.assertNotIn("ada@example.invalid", repr(config))

    def test_config_rejects_unsafe_file_and_embedded_password(self) -> None:
        with TemporaryDirectory() as folder:
            file = Path(folder) / "pilot.json"
            _write_config(file, _payload())
            file.chmod(0o644)
            with self.assertRaises(CalendarConnectionConfigurationError):
                load_connection_config(file)
            file.chmod(0o600)

            symlink = Path(folder) / "link.json"
            symlink.symlink_to(file)
            with self.assertRaises(CalendarConnectionConfigurationError):
                load_connection_config(symlink)

            with self.assertRaises(CalendarConnectionConfigurationError):
                load_connection_config(Path(folder) / "missing.json")

            bad = _payload()
            bad["password"] = "never store a password here"
            _write_config(file, bad)
            with self.assertRaises(CalendarConnectionConfigurationError):
                load_connection_config(file)

    def test_config_rejects_cross_origin_ambiguous_or_invalid_data(self) -> None:
        cases = [
            ("base_url", "http://dav.example.invalid"),
            ("base_url", "https://user:password@dav.example.invalid"),
            ("base_url", "https://dav.example.invalid/?token=value"),
            ("username", "user:illegal"),
            ("password_ref", ""),
            ("provider", "other"),
        ]
        with TemporaryDirectory() as folder:
            file = Path(folder) / "pilot.json"
            for field, value in cases:
                with self.subTest(field=field, value=value):
                    bad = _payload()
                    bad[field] = value
                    _write_config(file, bad)
                    with self.assertRaises(CalendarConnectionConfigurationError):
                        load_connection_config(file)

            for collection in ("https://evil.example.invalid/cal", "//evil.example/cal", "/foo?bar"):
                with self.subTest(collection=collection):
                    bad = _payload()
                    bad["calendars"][0]["collection"] = collection
                    _write_config(file, bad)
                    with self.assertRaises(CalendarConnectionConfigurationError):
                        load_connection_config(file)

            duplicated = _payload()
            duplicated["calendars"][1]["id"] = "family"
            _write_config(file, duplicated)
            with self.assertRaises(CalendarConnectionConfigurationError):
                load_connection_config(file)


class CalDAVProbeTests(unittest.TestCase):
    def _config(self) -> CalendarConnectionConfig:
        return CalendarConnectionConfig(
            base_url=BASE_URL,
            username="ada@example.invalid",
            password_ref="ionos/calendar",
            calendars=(default_family_ref(), default_read_only_ref()),
        )

    def test_probe_reads_event_count_without_details_or_write(self) -> None:
        server = build_fake_server()
        server.seed_resource(
            FAMILY_PATH, "one.ics",
            b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\n"
            b"UID:one@example.invalid\r\nDTSTAMP:20261001T080000Z\r\n"
            b"DTSTART:20261002T090000Z\r\n"
            b"DTEND:20261002T100000Z\r\nSUMMARY:Synthetic secret title\r\n"
            b"END:VEVENT\r\nEND:VCALENDAR\r\n",
        )
        methods = []

        def record(request: httpx2.Request) -> httpx2.Response:
            methods.append(request.method)
            return server(request)

        result = probe_connection(
            self._config(), "synthetic-password",
            transport=httpx2.MockTransport(record),
            now=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(result, (2, 1))
        self.assertEqual(methods, ["PROPFIND", "PROPFIND", "REPORT", "REPORT"])
        self.assertEqual(server.put_attempts, 0)
        self.assertEqual(server.conditional_writes, [])

    def test_probe_refuses_provider_privilege_mismatch_before_report(self) -> None:
        for configured_path, privileges in (
            (FAMILY_PATH, frozenset({"read"})),
            (READ_ONLY_PATH, frozenset({"read", "write"})),
        ):
            with self.subTest(path=configured_path):
                server = build_fake_server()
                server.add_collection(configured_path, privileges=privileges)
                with self.assertRaises(CalDAVConfigurationError):
                    probe_connection(
                        self._config(), "synthetic-password",
                        transport=httpx2.MockTransport(server),
                        now=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    )
                self.assertEqual(server.received_time_ranges, [])
                self.assertEqual(server.put_attempts, 0)

    def test_probe_fails_closed_without_server_credentials(self) -> None:
        def reject(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(401, content=b"authentication refused")

        with self.assertRaises(CalDAVProtocolError):
            probe_connection(
                self._config(), "synthetic-password",
                transport=httpx2.MockTransport(reject),
                now=datetime(2026, 10, 1, tzinfo=timezone.utc),
            )

    def test_cli_never_exposes_password_or_provider_payload(self) -> None:
        class FakeVault:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def password(self, reference: str) -> str:
                if reference != "ionos/calendar":
                    raise AssertionError("incorrect allowlist")
                return "synthetic-sensitive-value"

        with TemporaryDirectory() as folder:
            config_file = Path(folder) / "pilot.json"
            _write_config(config_file, _payload())
            stdout, stderr = StringIO(), StringIO()
            with (
                patch("ada.cli._unlock_vault", return_value=FakeVault()) as unlock,
                patch(
                    "ada.application.calendar_connection.probe_connection",
                    return_value=(2, 1),
                ) as connection,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = _calendar_probe(folder, str(config_file))
            self.assertEqual(result, 0)
            self.assertEqual(
                unlock.call_args.kwargs["allowed_entries"],
                frozenset({"ionos/calendar"}),
            )
            self.assertEqual(connection.call_args.args[1], "synthetic-sensitive-value")
            self.assertIn("2 collections, 1 events", stdout.getvalue())
            self.assertNotIn("ada@example.invalid", stdout.getvalue())
            self.assertNotIn("ionos/calendar", stdout.getvalue())
            self.assertNotIn("synthetic-sensitive-value", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

            with (
                patch("ada.cli._unlock_vault", return_value=FakeVault()),
                patch(
                    "ada.application.calendar_connection.probe_connection",
                    side_effect=RuntimeError(
                        "provider error: synthetic-sensitive-value"
                    ),
                ),
                redirect_stdout(stdout := StringIO()),
                redirect_stderr(stderr := StringIO()),
            ):
                self.assertEqual(_calendar_probe(folder, str(config_file)), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertNotIn("synthetic-sensitive-value", stderr.getvalue())
            self.assertIn("no calendar changes attempted", stderr.getvalue())

    def test_parser_requires_an_explicit_config_and_root(self) -> None:
        args = build_parser().parse_args(
            ["calendar-probe", "--config", "/pilot.json", "--memory-root", "/memory"]
        )
        self.assertEqual(args.command, "calendar-probe")
        self.assertEqual(args.config, "/pilot.json")
        with self.assertRaises(SystemExit):
            with redirect_stderr(StringIO()):
                build_parser().parse_args(["calendar-probe"])


if __name__ == "__main__":
    unittest.main()
