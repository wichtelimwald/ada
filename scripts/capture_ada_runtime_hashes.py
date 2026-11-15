#!/usr/bin/env python3
"""Capture exact target-platform wheel hashes for Ada + KDBX + build backend.

No installation or repository file mutation. Output is a candidate lock for
review, NOT a software security audit. Run on CPython 3.14/Linux/aarch64.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAME = "requirements/ada-runtime-py314-linux-aarch64.txt"
KDBX_LOCK_NAME = "requirements/kdbx-py314-linux-aarch64.txt"
_LINE = re.compile(r"([a-z0-9-]+)==([0-9.]+) --hash=sha256:([a-f0-9]{64})")


def _name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _pins_from_lock(path: Path) -> dict[str, tuple[str, str]]:
    pins: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = _LINE.fullmatch(line)
        if match is None:
            raise SystemExit(f"Invalid committed hash lock entry in {path}")
        name, version, digest = match.groups()
        if name in pins:
            raise SystemExit(f"Duplicate locked dependency: {name}")
        pins[name] = (version, digest)
    if not pins:
        raise SystemExit(f"Empty dependency lock: {path}")
    return pins


def main() -> int:
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 14)
        or sys.platform != "linux"
        or platform.machine() != "aarch64"
    ):
        raise SystemExit("CPython 3.14 on Linux/aarch64 required")

    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    requirements = [
        *project["project"]["dependencies"],
        *project["project"]["optional-dependencies"]["secrets-poc"],
        *project["build-system"]["requires"],
    ]
    kdbx_pins = _pins_from_lock(PROJECT_ROOT / KDBX_LOCK_NAME)

    with TemporaryDirectory(prefix="ada-runtime-lock-") as directory:
        root = Path(directory)
        report = root / "resolution.json"
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
                "--report",
                str(report),
                *requirements,
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )
        resolved = json.loads(report.read_text(encoding="utf-8"))["install"]

        found: dict[str, tuple[str, str]] = {}
        for item in resolved:
            metadata = item["metadata"]
            name = _name(metadata["name"])
            version = metadata["version"]
            source = item["download_info"]
            url = urlparse(source["url"])
            hashes = source.get("archive_info", {}).get("hashes", {})
            digest = hashes.get("sha256")
            if (
                name in found
                or not re.fullmatch(r"[0-9][0-9A-Za-z.!+_-]*", version)
                or url.scheme != "https"
                or url.hostname not in {"files.pythonhosted.org", "pypi.org"}
                or not url.path.endswith(".whl")
                or not isinstance(digest, str)
                or not re.fullmatch(r"[a-fA-F0-9]{64}", digest)
            ):
                raise SystemExit(f"Unexpected wheel/resolution for {name}")
            found[name] = (version, digest.lower())

        if len(found) < len(kdbx_pins) or not set(kdbx_pins).issubset(found):
            raise SystemExit("KDBX reader dependency graph is incomplete")
        for name, expected in kdbx_pins.items():
            if found[name] != expected:
                raise SystemExit(f"Existing KDBX hash/version changed: {name}")
        if "setuptools" not in found:
            raise SystemExit("The PEP 517 build backend must be hash-pinned")

        content = (
            "# CPython 3.14, Linux/aarch64: Ada runtime, KDBX reader, setuptools.\n"
            "# Includes all transitives in pip's resolved graph. REVIEW BEFORE USE.\n"
            + "".join(
                f"{name}=={version} --hash=sha256:{digest}\n"
                for name, (version, digest) in sorted(found.items())
            )
        )

        # Verify all pins with pip in hash-checking mode, without installing.
        candidate = root / "candidate.txt"
        candidate.write_text(content, encoding="utf-8")
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
                str(candidate),
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )

    committed = PROJECT_ROOT / OUTPUT_NAME
    if committed.is_file() and committed.read_text(encoding="utf-8") != content:
        raise SystemExit(f"Resolution differs from committed {OUTPUT_NAME}")
    print(f"Verified full candidate ({len(found)} wheels): {OUTPUT_NAME}")
    print(content)
    print("No packages installed and no repository files modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
