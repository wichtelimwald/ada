"""Development-only IONOS CalDAV composition (MVP-60 S6, ADR-0009).

Only non-secret configuration is read from disk. The IONOS app password comes
from the host macOS Keychain, never an environment variable or TOML field.
This module does not enable a family-facing action path or live writes.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx2

from ada.adapters.caldav.adapter import CalDAVCalendarAdapter
from ada.adapters.caldav.profile import IONOS_PROFILE
from ada.ports.calendar import CalendarAccessMode, CalendarAudience, CalendarRef


_IONOS_URL = "https://dav.mailbusiness.ionos.de"
_MAX_CONFIG_BYTES = 32_768
_CALENDAR_ID = re.compile(r"[a-z][a-z0-9_-]*\Z")
_COLLECTION_PATH = re.compile(r"/caldav/[A-Za-z0-9._~%-]+/?\Z")


class IONOSDevelopmentConfigurationError(ValueError):
    """A local configuration or required Keychain credential is unavailable."""


@dataclass(frozen=True, slots=True)
class IONOSDevelopmentSettings:
    mailbox: str = field(repr=False)
    base_url: str = _IONOS_URL
    calendars: tuple[CalendarRef, ...] = field(default=(), repr=False)


def _load_owned_toml(path: Path) -> dict[str, Any]:
    """Read a regular, owner-only file without following the final symlink."""

    # Fail closed if no-follow semantics are unavailable on the target host.
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        raise IONOSDevelopmentConfigurationError(
            "CalDAV configuration is missing or cannot be opened"
        ) from None

    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > _MAX_CONFIG_BYTES
        ):
            raise IONOSDevelopmentConfigurationError(
                "CalDAV configuration must be an owner-owned regular file with mode 0600"
            )
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            contents = handle.read(_MAX_CONFIG_BYTES + 1)
        if len(contents) > _MAX_CONFIG_BYTES:
            raise IONOSDevelopmentConfigurationError("CalDAV configuration exceeds size limit")
        parsed = tomllib.loads(contents.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError):
        raise IONOSDevelopmentConfigurationError(
            "Invalid CalDAV configuration TOML"
        ) from None
    finally:
        if fd >= 0:
            os.close(fd)

    if not isinstance(parsed, dict):
        raise IONOSDevelopmentConfigurationError("Invalid CalDAV configuration")
    return parsed


def load_ionos_development_settings(path: Path) -> IONOSDevelopmentSettings:
    """Strictly parse non-secret IONOS settings; reject unknown keys."""

    data = _load_owned_toml(path)
    if set(data) != {"version", "mailbox", "base_url", "calendar"}:
        raise IONOSDevelopmentConfigurationError(
            "Expected version, mailbox, base_url and calendar entries only"
        )
    if type(data["version"]) is not int or data["version"] != 1:
        raise IONOSDevelopmentConfigurationError("Unsupported CalDAV configuration version")

    mailbox = data["mailbox"]
    url = data["base_url"]
    if (
        not isinstance(mailbox, str)
        or not mailbox.strip()
        or any(char in mailbox for char in "\r\n\0")
    ):
        raise IONOSDevelopmentConfigurationError("Invalid IONOS mailbox")
    if not isinstance(url, str) or url not in {_IONOS_URL, _IONOS_URL + "/"}:
        raise IONOSDevelopmentConfigurationError(
            "IONOS credentials can only be used with the pinned CalDAV HTTPS origin"
        )

    items = data["calendar"]
    if not isinstance(items, list) or not items:
        raise IONOSDevelopmentConfigurationError("At least one calendar is required")

    calendars: list[CalendarRef] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "id", "collection", "audience", "access"
        }:
            raise IONOSDevelopmentConfigurationError("Invalid calendar mapping")
        ident, collection = item["id"], item["collection"]
        if (
            not isinstance(ident, str)
            or not _CALENDAR_ID.fullmatch(ident)
            or ident in seen
            or not isinstance(collection, str)
            or not _COLLECTION_PATH.fullmatch(collection)
            or collection in {"/caldav/.", "/caldav/.."}
        ):
            raise IONOSDevelopmentConfigurationError("Invalid or duplicate calendar mapping")
        try:
            audience = CalendarAudience(item["audience"])
            access = CalendarAccessMode(item["access"])
        except (ValueError, TypeError):
            raise IONOSDevelopmentConfigurationError(
                "Invalid calendar audience or access mode"
            ) from None
        seen.add(ident)
        calendars.append(
            CalendarRef(
                calendar_id=ident,
                provider_collection=collection,
                audience=audience,
                access_mode=access,
            )
        )
    return IONOSDevelopmentSettings(
        mailbox=mailbox, base_url=_IONOS_URL, calendars=tuple(calendars)
    )


def read_ionos_keychain_password(mailbox: str) -> str:
    """Find the existing ada-caldav item via macOS security, without shell or env.

    This intentionally has no Linux/development-container fallback for real
    credentials; tests inject a synthetic reader instead.
    """

    if sys.platform != "darwin":
        raise IONOSDevelopmentConfigurationError(
            "Real IONOS credentials require the macOS Keychain"
        )
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s", "ada-caldav",
                "-a", mailbox,
                "-w",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise IONOSDevelopmentConfigurationError(
            "IONOS Keychain item is unavailable"
        ) from None

    if result.returncode != 0:
        raise IONOSDevelopmentConfigurationError(
            "IONOS Keychain item is unavailable"
        )
    # The security CLI appends a line ending; preserve any other characters.
    try:
        password = result.stdout.removesuffix(b"\n").removesuffix(b"\r").decode(
            "utf-8", errors="strict"
        )
    except UnicodeError:
        raise IONOSDevelopmentConfigurationError(
            "IONOS Keychain item cannot be decoded"
        ) from None
    if not password:
        raise IONOSDevelopmentConfigurationError("IONOS Keychain item is empty")
    return password


def build_development_ionos_adapter(
    config_path: Path,
    *,
    password_reader: Callable[[str], str] = read_ionos_keychain_password,
    transport: httpx2.BaseTransport | None = None,
) -> CalDAVCalendarAdapter:
    """Compose the existing adapter without initiating provider requests.

    The destination and calendar paths are pinned and validated before the
    credential is read. Tests can inject only a synthetic password reader.
    This constructor is not a security gate for writes: its caller must not
    expose the adapter to real actions before S6/S7 durable-state, authority
    and acceptance gates have passed.
    """

    config = load_ionos_development_settings(config_path)
    password = password_reader(config.mailbox)
    if not isinstance(password, str) or not password:
        raise IONOSDevelopmentConfigurationError("IONOS Keychain item is empty")
    return CalDAVCalendarAdapter(
        base_url=config.base_url,
        auth=(config.mailbox, password),
        calendars=config.calendars,
        profile=IONOS_PROFILE,
        transport=transport,
    )
