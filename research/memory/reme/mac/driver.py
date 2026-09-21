#!/usr/bin/env python3
"""Black-box helpers for the Ada/ReMe macOS research spike.

This file intentionally uses only the Python standard library so it can run
outside the ReMe virtual environment as well as inside it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _post(base_url: str, endpoint: str, payload: dict, *, timeout: float = 20.0) -> dict:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{endpoint}: expected JSON object, got {type(parsed).__name__}")
    return parsed


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _expect_success(response: dict, label: str) -> None:
    if response.get("success") is not True:
        raise RuntimeError(f"{label} failed: {json.dumps(response, ensure_ascii=False)}")


def _search_blob(response: dict) -> str:
    """Return only returned Memory material, not the echoed request/query."""
    answer = response.get("answer", "")
    metadata = response.get("metadata") or {}
    results = metadata.get("results") or []
    return f"{answer}\n{json.dumps(results, ensure_ascii=False)}"


def _wait_for_service(base_url: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = _post(base_url, "version", {})
            if response.get("success") is True:
                return response
            last_error = RuntimeError(json.dumps(response))
        except (OSError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"ReMe service did not become ready at {base_url}: {last_error}")


def _wait_for_search(
    base_url: str,
    query: str,
    *,
    contains: str | None = None,
    absent: str | None = None,
    timeout: float = 20.0,
) -> dict:
    deadline = time.monotonic() + timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        last = _post(base_url, "search", {"query": query, "limit": 10})
        _expect_success(last, "search")
        blob = _search_blob(last)
        contains_ok = contains is None or contains in blob
        absent_ok = absent is None or absent not in blob
        if contains_ok and absent_ok:
            return last
        time.sleep(0.5)
    raise RuntimeError(
        "search condition not reached: "
        f"query={query!r} contains={contains!r} absent={absent!r} "
        f"last={json.dumps(last, ensure_ascii=False)}"
    )


def cmd_wait(args: argparse.Namespace) -> None:
    response = _wait_for_service(args.base_url, args.timeout)
    _write_json(args.out, response)


def cmd_basic(args: argparse.Namespace) -> None:
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    rel_path = "digest/wiki/ada-reme-spike-basic.md"
    old_token = args.old_token

    response = _post(
        args.base_url,
        "write",
        {
            "path": rel_path,
            "name": "Ada ReMe Spike Basic",
            "description": "Synthetic Ada/ReMe characterization memory.",
            "content": (
                "# Ada ReMe Spike Basic\n\n"
                f"Synthetic source-of-truth canary: {old_token}\n\n"
                "This fixture contains no personal data.\n"
            ),
        },
    )
    _expect_success(response, "write")
    _write_json(out / "write.json", response)

    search = _wait_for_search(args.base_url, old_token, contains=old_token)
    _write_json(out / "search-before-edit.json", search)

    fm = _post(
        args.base_url,
        "frontmatter_update",
        {
            "path": rel_path,
            "metadata": {
                "ada": {
                    "state": "provisional",
                    "confirmation_basis": "observed_pattern",
                    "subject": "synthetic-person-a",
                }
            },
        },
    )
    _expect_success(fm, "frontmatter_update")
    _write_json(out / "frontmatter-update.json", fm)

    source = args.workspace / rel_path
    text = source.read_text(encoding="utf-8")
    for needle in (
        "state: provisional",
        "confirmation_basis: observed_pattern",
        "subject: synthetic-person-a",
        old_token,
    ):
        if needle not in text:
            raise RuntimeError(f"frontmatter/source preservation failed; missing {needle!r} in {source}")
    (out / "source-after-frontmatter.md").write_text(text, encoding="utf-8")

    fm_read = _post(args.base_url, "frontmatter_read", {"path": rel_path})
    _expect_success(fm_read, "frontmatter_read")
    _write_json(out / "frontmatter-read.json", fm_read)


def cmd_mutate(args: argparse.Namespace) -> None:
    source = args.workspace / "digest/wiki/ada-reme-spike-basic.md"
    text = source.read_text(encoding="utf-8")
    if args.old_token not in text:
        raise RuntimeError(f"expected old canary not found before outside edit: {args.old_token}")
    text = text.replace(args.old_token, args.new_token)
    text = text.replace("state: provisional", "state: confirmed")
    source.write_text(text, encoding="utf-8")


def cmd_search(args: argparse.Namespace) -> None:
    response = _wait_for_search(
        args.base_url,
        args.query,
        contains=args.contains,
        absent=args.absent,
        timeout=args.timeout,
    )
    _write_json(args.out, response)


def _write_canary(base_url: str, path: str, name: str, token: str) -> None:
    response = _post(
        base_url,
        "write",
        {
            "path": path,
            "name": name,
            "description": "Synthetic protection-domain isolation fixture.",
            "content": f"# {name}\n\nPrivate synthetic canary: {token}\n",
        },
    )
    _expect_success(response, f"write {name}")
    _wait_for_search(base_url, token, contains=token)


def cmd_isolation(args: argparse.Namespace) -> None:
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    _write_canary(args.base_a, "digest/personal/private-a.md", "Private A", args.token_a)
    _write_canary(args.base_b, "digest/personal/private-b.md", "Private B", args.token_b)

    a_own = _wait_for_search(args.base_a, args.token_a, contains=args.token_a)
    b_own = _wait_for_search(args.base_b, args.token_b, contains=args.token_b)
    a_cross = _wait_for_search(args.base_a, args.token_b, absent=args.token_b)
    b_cross = _wait_for_search(args.base_b, args.token_a, absent=args.token_a)

    _write_json(out / "a-own.json", a_own)
    _write_json(out / "b-own.json", b_own)
    _write_json(out / "a-cross.json", a_cross)
    _write_json(out / "b-cross.json", b_cross)


def cmd_llm(args: argparse.Namespace) -> None:
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    day = args.date

    cases = [
        (
            "preference",
            "ada-spike-preference",
            [
                {
                    "name": "user",
                    "role": "user",
                    "content": (
                        "Synthetic characterization fixture only. "
                        "The test persona explicitly prefers concise bullet-point status updates. "
                        f"Evidence token: {args.preference_token}"
                    ),
                },
                {"name": "assistant", "role": "assistant", "content": "Understood."},
            ],
            "Record the explicit communication preference and its synthetic evidence token.",
        ),
        (
            "correction-before",
            "ada-spike-correction",
            [
                {
                    "name": "user",
                    "role": "user",
                    "content": (
                        "Synthetic fixture: the music lesson is Wednesday at 17:00. "
                        f"Evidence token: {args.correction_token}"
                    ),
                },
                {"name": "assistant", "role": "assistant", "content": "Recorded."},
            ],
            "Record the synthetic schedule fact.",
        ),
        (
            "correction-after",
            "ada-spike-correction",
            [
                {
                    "name": "user",
                    "role": "user",
                    "content": (
                        "Correction to the synthetic fixture: not Wednesday. "
                        "The music lesson is Thursday at 17:00."
                    ),
                },
                {"name": "assistant", "role": "assistant", "content": "Recorded correction."},
            ],
            "Apply the explicit correction to the same synthetic schedule fact.",
        ),
        (
            "conflict-a",
            "ada-spike-conflict-a",
            [
                {
                    "name": "user",
                    "role": "user",
                    "content": (
                        "Synthetic unresolved-conflict fixture: pickup is at 16:00. "
                        f"Evidence token: {args.conflict_token}"
                    ),
                },
                {"name": "assistant", "role": "assistant", "content": "Recorded."},
            ],
            "Record this synthetic pickup-time claim without inventing clarification.",
        ),
        (
            "conflict-b",
            "ada-spike-conflict-b",
            [
                {
                    "name": "user",
                    "role": "user",
                    "content": "Synthetic unresolved-conflict fixture: pickup is at 17:00.",
                },
                {"name": "assistant", "role": "assistant", "content": "Recorded."},
            ],
            "Record this second synthetic pickup-time claim without assuming it corrects another source.",
        ),
    ]

    for label, session_id, messages, hint in cases:
        response = _post(
            args.base_url,
            "auto_memory",
            {"session_id": session_id, "messages": messages, "memory_hint": hint, "date": day},
            timeout=args.llm_timeout,
        )
        _expect_success(response, f"auto_memory {label}")
        _write_json(out / f"auto-memory-{label}.json", response)

    dream = _post(
        args.base_url,
        "auto_dream",
        {
            "date": day,
            "hint": (
                "Characterization run. Preserve provenance. Do not infer authorization. "
                "Do not treat the two pickup claims as an explicit correction unless the evidence says so."
            ),
            "scan_days": 1,
            "max_units": 10,
        },
        timeout=args.dream_timeout,
    )
    _expect_success(dream, "auto_dream")
    _write_json(out / "auto-dream.json", dream)

    for directory in ("daily", "digest", "session"):
        root = args.workspace / directory
        snapshot = out / f"{directory}-snapshot"
        if not root.exists():
            continue
        for source in root.rglob("*"):
            if not source.is_file():
                continue
            rel = source.relative_to(root)
            target = snapshot / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            except UnicodeDecodeError:
                target.with_suffix(target.suffix + ".binary-marker").write_text(
                    f"binary file omitted: {source}\n", encoding="utf-8"
                )


def cmd_status(args: argparse.Namespace) -> None:
    response = _post(args.base_url, "status", {})
    _expect_success(response, "status")
    _write_json(args.out, response)


def cmd_summary(args: argparse.Namespace) -> None:
    rows: list[dict[str, str]] = []
    for raw in args.steps.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        name, status, seconds = parts[:3]
        rows.append({"name": name, "status": status, "seconds": seconds})

    payload = {
        "result_dir": str(args.result_dir),
        "overall": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FINDINGS",
        "steps": rows,
    }
    _write_json(args.result_dir / "summary.json", payload)

    lines = [
        "# Ada/ReMe macOS spike summary",
        "",
        f"Overall: **{payload['overall']}**",
        "",
        "| Step | Status | Seconds |",
        "| --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(f"| {row['name']} | {row['status']} | {row['seconds']} |")
    lines.extend(
        [
            "",
            "A FAIL here is a research finding, not automatically a ReMe rejection.",
            "Inspect the corresponding log and captured artifacts before drawing an architecture conclusion.",
            "",
        ]
    )
    (args.result_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("wait")
    p.add_argument("--base-url", required=True)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_wait)

    p = sub.add_parser("basic")
    p.add_argument("--base-url", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--old-token", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_basic)

    p = sub.add_parser("mutate")
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--old-token", required=True)
    p.add_argument("--new-token", required=True)
    p.set_defaults(func=cmd_mutate)

    p = sub.add_parser("search")
    p.add_argument("--base-url", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--contains")
    p.add_argument("--absent")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("isolation")
    p.add_argument("--base-a", required=True)
    p.add_argument("--base-b", required=True)
    p.add_argument("--token-a", required=True)
    p.add_argument("--token-b", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_isolation)

    p = sub.add_parser("llm")
    p.add_argument("--base-url", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--preference-token", required=True)
    p.add_argument("--correction-token", required=True)
    p.add_argument("--conflict-token", required=True)
    p.add_argument("--llm-timeout", type=float, default=300.0)
    p.add_argument("--dream-timeout", type=float, default=600.0)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_llm)

    p = sub.add_parser("status")
    p.add_argument("--base-url", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("summary")
    p.add_argument("--steps", type=Path, required=True)
    p.add_argument("--result-dir", type=Path, required=True)
    p.set_defaults(func=cmd_summary)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
