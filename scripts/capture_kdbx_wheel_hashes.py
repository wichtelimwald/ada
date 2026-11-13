#!/usr/bin/env python3
"""Capture platform-specific KDBX wheel hashes without installing packages.

Run only in Ada's Python 3.14 Linux/aarch64 research container.
Output is a proposed lockfile, NOT a dependency-security approval.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


# Versions from the maintainer's synthetic Docker test (PR #57).
# Each package is explicit, so changes to the transitive graph fail closed.
PINS = {
    "kdbxtool": "0.1.7",
    "argon2-cffi": "25.1.0",
    "argon2-cffi-bindings": "26.2.0",
    "cffi": "2.1.1",
    "pycparser": "3.12",
    "pycryptodomex": "3.24.2",
    "defusedxml": "0.7.1",
}
OUTPUT = Path("requirements/kdbx-py314-linux-aarch64.txt")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def main() -> int:
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 14)
        or sys.platform != "linux"
        or platform.machine() != "aarch64"
    ):
        raise SystemExit("Run only with CPython 3.14 on Linux/aarch64")

    with TemporaryDirectory(prefix="ada-kdbx-lock-") as directory:
        report = Path(directory) / "pip-report.json"
        command = [
            sys.executable,
            "-m",
            "pip",
            "--isolated",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--only-binary=:all:",
            "--index-url",
            "https://pypi.org/simple",
            "--report",
            str(report),
            *(f"{name}=={version}" for name, version in PINS.items()),
        ]
        subprocess.run(command, check=True)
        records = json.loads(report.read_text(encoding="utf-8"))["install"]

    found: dict[str, tuple[str, str]] = {}
    for record in records:
        metadata = record["metadata"]
        name = normalized(metadata["name"])
        version = metadata["version"]
        source = record["download_info"]
        url = urlparse(source["url"])
        digest = source["archive_info"].get("hashes", {}).get("sha256")
        if not digest:
            legacy_hash = source["archive_info"].get("hash", "")
            if legacy_hash.startswith("sha256="):
                digest = legacy_hash.removeprefix("sha256=")
        if (
            name not in PINS
            or name in found
            or version != PINS[name]
            or url.scheme != "https"
            or url.hostname not in {"files.pythonhosted.org", "pypi.org"}
            or not url.path.endswith(".whl")
            or not isinstance(digest, str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", digest)
        ):
            raise SystemExit(f"Unexpected or unverified wheel metadata: {name}")
        found[name] = (version, digest.lower())

    if set(found) != set(PINS):
        raise SystemExit(
            f"Dependency graph changed: missing={sorted(set(PINS) - set(found))}"
        )

    contents = (
        "# Generated for CPython 3.14 on Linux/aarch64 only.\n"
        "# Exact PyPI wheel hashes; NOT a security audit or production approval.\n"
        "# Use with: python -m pip install --require-hashes -r <this-file>\n"
        + "".join(
            f"{name}=={found[name][0]} --hash=sha256:{found[name][1]}\n"
            for name in sorted(found)
        )
    )

    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != contents:
        raise SystemExit(f"{OUTPUT} differs; review explicitly before replacing")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(contents, encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(found)} verified wheel hashes.")
    print(contents)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "--isolated",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--only-binary=:all:",
            "--index-url",
            "https://pypi.org/simple",
            "--require-hashes",
            "-r",
            str(OUTPUT),
        ],
        check=True,
    )
    print("Hash-locked dry-run resolution passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
