#!/usr/bin/env python3
"""Fail a credential image build if its installed Python graph differs from lock.

Run only in the image, after installing Ada offline. Uses the standard library
and never reads vaults or imports application code.
"""

from __future__ import annotations

import importlib.metadata as metadata
import re
from pathlib import Path


LOCK = Path("/app/requirements/ada-runtime-py314-linux-aarch64.txt")
ENTRY = re.compile(r"([a-z0-9-]+)==([^ ]+) --hash=sha256:[0-9a-f]{64}")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def locked_versions(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = ENTRY.fullmatch(line)
        if match is None:
            raise ValueError("Invalid credential runtime lock line")
        name, version = match.groups()
        if name in values:
            raise ValueError("Duplicate locked Python distribution")
        values[name] = version
    if not values or "setuptools" not in values or "kdbxtool" not in values:
        raise ValueError("Missing build backend or KDBX reader in runtime lock")
    return values


def main() -> int:
    locked = locked_versions(LOCK)
    installed: dict[str, str] = {}
    for package in metadata.distributions():
        name = normalized(package.metadata["Name"])
        if name in installed:
            raise SystemExit("Duplicate installed Python distribution")
        installed[name] = package.version

    # pip is supplied by the pinned Python base; Ada itself is local source.
    unreviewed = set(installed) - set(locked) - {"pip", "ada-assistant"}
    missing = set(locked) - set(installed)
    changed = {
        name: (version, installed.get(name))
        for name, version in locked.items()
        if installed.get(name) != version
    }
    if unreviewed or missing or changed or installed.get("ada-assistant") != "0.0.1":
        raise SystemExit(
            "Credential image dependency inventory mismatch: "
            f"unreviewed={sorted(unreviewed)} missing={sorted(missing)} "
            f"changed={changed}"
        )
    print(f"Credential runtime inventory: {len(locked)} hash-locked packages plus base pip and local Ada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
