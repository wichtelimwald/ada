#!/usr/bin/env python3
"""Fail closed on absent release pins; does not itself attest wheel licenses."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKS = (
    "requirements-macos-arm64.txt",
    "requirements-linux-amd64.txt",
    "requirements-linux-arm64.txt",
)
PIN = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==[^\s\\]+\s+"
    r"(?:--hash=sha256:[0-9a-f]{64}\s*)+$"
)
BASE = re.compile(r"^FROM python:3\.14-slim@sha256:[0-9a-f]{64} AS base$", re.M)


def check() -> list[str]:
    errors: list[str] = []
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["dependencies"]
    top_level = {
        re.split(r"\[|==", dep, maxsplit=1)[0].lower().replace("_", "-")
        for dep in deps
    }
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    if BASE.search(dockerfile) is None:
        errors.append("Dockerfile base image lacks a reviewed sha256 digest")

    for filename in LOCKS:
        path = ROOT / "release-locks" / filename
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
            continue
        # A requirements entry may be continued over multiple lines by uv
        # or pip-tools. This check only accepts exact pins with SHA256 hashes.
        lines = path.read_text(encoding="utf-8").splitlines()
        entries: list[str] = []
        pending = ""
        for line in lines:
            line = line.split("#", maxsplit=1)[0].strip()
            if not line:
                continue
            pending += " " + line.rstrip("\\").strip()
            if line.endswith("\\"):
                continue
            entries.append(" ".join(pending.split()))
            pending = ""
        if pending or not entries:
            errors.append(f"{filename}: empty or unterminated requirements")
        found: set[str] = set()
        for entry in entries:
            match = PIN.fullmatch(entry)
            if match is None:
                errors.append(f"{filename}: unpinned or unhashed requirement")
                continue
            found.add(match.group(1).lower().replace("_", "-"))
        if missing := top_level - found:
            errors.append(f"{filename}: missing top-level packages: {', '.join(sorted(missing))}")
    return errors


if __name__ == "__main__":
    problems = check()
    if problems:
        for problem in problems:
            print(f"release input gate: {problem}", file=sys.stderr)
        sys.exit(1)
    print("release input gate: static pins present; verify actual artifacts separately")
