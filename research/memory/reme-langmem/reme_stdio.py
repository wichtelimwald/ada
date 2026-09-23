#!/usr/bin/env python3
"""Research-only ReMe stdio server with an internal Markdown index watcher."""

from __future__ import annotations

import argparse
from pathlib import Path

from reme.config import resolve_app_config
from reme.reme import ReMe


READ_TOOLS = ("version", "status", "search", "read")
INDEX_JOB = "index_update_loop"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    # The upstream Codex stdio bridge suppresses stdout logging but removes
    # every background job, including the only Markdown index watcher.
    config = resolve_app_config(
        config=args.config,
        workspace_dir=str(Path(args.workspace).absolute()),
        enable_logo=False,
        log_to_console=False,
        log_to_file=False,
        log_config=False,
    )
    source_jobs = config["jobs"]
    selected_jobs = (*READ_TOOLS, INDEX_JOB)
    missing = set(selected_jobs) - source_jobs.keys()
    if missing:
        raise KeyError(f"Missing ReMe jobs: {sorted(missing)}")
    if source_jobs[INDEX_JOB].get("backend") != "background":
        raise ValueError("ReMe Markdown index job is no longer a background job")

    config["jobs"] = {name: dict(source_jobs[name]) for name in selected_jobs}
    for name in READ_TOOLS:
        config["jobs"][name]["enable_serve"] = True
    config["service"] = {
        "backend": "mcp",
        "transport": "stdio",
        "jobs": list(READ_TOOLS),
        "tool_error_on_failure": True,
    }
    ReMe(**config).run_app()


if __name__ == "__main__":
    main()
