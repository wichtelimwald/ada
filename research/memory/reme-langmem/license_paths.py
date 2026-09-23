#!/usr/bin/env python3
"""Trace five license findings in an existing combined Ada research venv.

Read-only: uses the recorded inventory and installed wheel file lists. It does
not install, import, or execute any of the candidate packages.
"""

from __future__ import annotations

import argparse
from collections import deque
import importlib.metadata as metadata
import json
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


TARGETS = ("psycopg", "psycopg-binary", "bidict", "certifi", "orjson")
BASE = (("ada-assistant", ()),)
ADDED = (("reme-ai", ("as",)), ("langmem", ()), ("langchain-ollama", ()))


def paths(
    packages: dict, roots: tuple[tuple[str, tuple[str, ...]], ...]
) -> tuple[dict[str, list[str]], list[str]]:
    queue = deque((canonicalize_name(name), extras, [name]) for name, extras in roots)
    visited: set[tuple[str, tuple[str, ...]]] = set()
    found: dict[str, list[str]] = {}
    missing: list[str] = []
    env = default_environment()

    while queue:
        name, extras, chain = queue.popleft()
        key = (name, tuple(sorted(extras)))
        if key in visited:
            continue
        visited.add(key)
        item = packages.get(name)
        if item is None:
            missing.append(" -> ".join(chain))
            continue
        found.setdefault(name, chain)
        for raw in item.get("requires", []):
            req = Requirement(raw)
            if req.marker and not any(
                req.marker.evaluate({**env, "extra": extra}) for extra in ("", *extras)
            ):
                continue
            child = canonicalize_name(req.name)
            queue.append((child, tuple(sorted(req.extras)), [*chain, req.name]))
    return found, missing


def installed_files(name: str) -> tuple[list[str], list[str]]:
    dist = metadata.distribution(name)
    files = [str(f) for f in (dist.files or [])]
    notices = [
        f for f in files
        if Path(f).name.lower().startswith(("license", "copying", "notice"))
    ]
    native = [
        f for f in files
        if f.lower().endswith((".so", ".dylib", ".dll", ".pyd"))
        or ".so." in f.lower()
    ]
    return notices, native


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir", type=Path,
        help="Existing artifacts/research/memory/reme-langmem/latest",
    )
    args = parser.parse_args()
    inventory = json.loads((args.run_dir / "inventory.json").read_text(encoding="utf-8"))
    packages = {canonicalize_name(p["name"]): p for p in inventory["packages"]}
    baseline, base_missing = paths(packages, BASE)
    combined, combined_missing = paths(packages, BASE + ADDED)
    if base_missing or combined_missing:
        raise SystemExit(f"Missing dependency metadata: {base_missing + combined_missing}")

    print("The baseline is reconstructed from combined-environment metadata, not a separate install.")
    print("A path indicates dependency attribution; it does not establish license compliance.\n")
    for name in TARGETS:
        key = canonicalize_name(name)
        item = packages.get(key)
        if item is None or key not in combined:
            raise SystemExit(f"Expected installed runtime distribution missing: {name}")
        notices, native = installed_files(name)
        print(f"{name}=={item['version']}: {'BASELINE' if key in baseline else 'NEW'}")
        license_text = item.get("license_expression") or item.get("license") or "not recorded"
        print("  Declared license: " + license_text)
        if key in baseline:
            print("  Ada path: " + " -> ".join(baseline[key]))
        print("  Combined path: " + " -> ".join(combined[key]))
        print("  License/notice files: " + (", ".join(notices) if notices else "NONE RECORDED"))
        print("  Native files: " + (", ".join(native) if native else "none recorded"))


if __name__ == "__main__":
    main()
