from __future__ import annotations

import argparse
import json
import platform
import sys

from ada import __version__


def _doctor() -> int:
    payload = {
        "status": "ok",
        "ada_version": __version__,
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ada",
        description="Ada local-first personal assistant",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "doctor",
        help="Print a local scaffold/runtime sanity check.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(_doctor())

    parser.print_help()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
