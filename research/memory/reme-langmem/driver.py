#!/usr/bin/env python3
"""Final ReMe + LangMem architecture characterization for ADR-0008.

Research-only code. It deliberately models the intended trust boundary rather
than production Ada APIs.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata as md
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Literal

import yaml
from fastmcp import Client
from fastmcp.client import StdioTransport
from langchain_ollama import ChatOllama
from langmem import create_memory_manager
from pydantic import BaseModel, Field


MUSIC_ID = "music-lesson"
PICKUP_ID = "pickup-16"

SRC_WED = "COMBO_SRC_WED_3B021C"
SRC_THU = "COMBO_SRC_THU_8C17A4"
SRC_16 = "COMBO_SRC_PICKUP16_29AF10"
SRC_17 = "COMBO_SRC_PICKUP17_BD74E1"

MARK_WED = "COMBO_CURRENT_WED_1CC802"
MARK_THU = "COMBO_CURRENT_THU_06C84F"
MARK_FRI = "COMBO_CURRENT_FRI_MANUAL_E7A901"
MARK_16 = "COMBO_PICKUP_16_4EF201"
MARK_17 = "COMBO_PICKUP_17_1AD637"


class MemoryRecord(BaseModel):
    """Model-owned semantic content only: deliberately no trust/security fields."""

    kind: Literal["preference", "fact"]
    subject: str = Field(description="Short neutral subject")
    statement: str = Field(description="Atomic semantic statement")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def atomic_markdown(path: Path, metadata: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
    text = f"---\n{frontmatter}\n---\n\n{body.rstrip()}\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def version_key(value: str) -> tuple[int, ...]:
    # Enough for the numeric security floors used by this research harness.
    nums = re.findall(r"\d+", value.split("+", 1)[0])
    return tuple(int(x) for x in nums)


def inventory(out: Path) -> None:
    rows = []
    review = []
    for dist in md.distributions():
        meta = dist.metadata
        name = meta.get("Name") or getattr(dist, "name", "")
        expression = meta.get("License-Expression")
        license_text = meta.get("License")
        classifiers = meta.get_all("Classifier") or []
        license_classifiers = [x for x in classifiers if x.startswith("License ::")]
        combined = " | ".join([expression or "", license_text or "", *license_classifiers]).strip()

        upper = combined.upper()
        if any(token in upper for token in ("AGPL", "GPL", "LGPL", "MPL", "SSPL", "EUPL")):
            license_status = "manual-review-nonpermissive-or-weak-copyleft"
        elif any(token in upper for token in ("MIT", "APACHE", "BSD", "ISC", "PSF", "UNLICENSE", "ZLIB")):
            license_status = "permissive-metadata"
        else:
            license_status = "manual-review-unknown-metadata"

        item = {
            "name": name,
            "version": dist.version,
            "license_expression": expression,
            "license": license_text,
            "license_classifiers": license_classifiers,
            "license_status": license_status,
            "requires": list(meta.get_all("Requires-Dist") or []),
        }
        rows.append(item)
        if license_status != "permissive-metadata":
            review.append({"name": name, "version": dist.version, "status": license_status, "metadata": combined})

    versions = {}
    for package in (
        "ada-assistant",
        "pydantic-ai-slim",
        "cedarpy",
        "dbos",
        "reme-ai",
        "agentscope",
        "langmem",
        "langchain-ollama",
        "langchain-core",
        "langgraph",
        "langgraph-checkpoint",
    ):
        try:
            versions[package] = md.version(package)
        except md.PackageNotFoundError:
            versions[package] = None

    checks = {
        "reme-ai==0.4.1.12": versions["reme-ai"] == "0.4.1.12",
        "agentscope==2.0.7.post1": versions["agentscope"] == "2.0.7.post1",
        "langmem==0.0.30": versions["langmem"] == "0.0.30",
        "langchain-ollama==1.1.0": versions["langchain-ollama"] == "1.1.0",
        "langchain-core>=1.3.3": bool(versions["langchain-core"]) and version_key(versions["langchain-core"]) >= version_key("1.3.3"),
        "langgraph>=1.0.10,<2": bool(versions["langgraph"]) and version_key(versions["langgraph"]) >= version_key("1.0.10") and version_key(versions["langgraph"]) < version_key("2"),
        "langgraph-checkpoint>=4.1.1": bool(versions["langgraph-checkpoint"]) and version_key(versions["langgraph-checkpoint"]) >= version_key("4.1.1"),
    }

    payload = {
        "python": sys.version,
        "distribution_count": len(rows),
        "selected_versions": versions,
        "security_floor_checks": checks,
        "all_security_floor_checks_pass": all(checks.values()),
        "manual_license_review": review,
        "packages": sorted(rows, key=lambda x: (x["name"] or "").lower()),
    }
    write_json(out, payload)
    if not all(checks.values()):
        raise RuntimeError(f"Security/version floor failed: {json.dumps(checks)}")


def proposal_rows(items) -> list[dict]:
    rows = []
    for item in items:
        content = item.content
        row = {"id": item.id, **content.model_dump(mode="json")}
        unexpected = set(row) - {"id", "kind", "subject", "statement"}
        if unexpected:
            raise RuntimeError(f"Model proposal escaped semantic schema: {sorted(unexpected)}")
        rows.append(row)
    return rows


def manager(model_name: str, ollama_host: str):
    model = ChatOllama(
        model=model_name,
        base_url=ollama_host,
        reasoning=False,
        temperature=0,
        num_predict=1536,
        keep_alive="10m",
    )
    return create_memory_manager(
        model,
        schemas=[MemoryRecord],
        instructions=(
            "Synthetic Ada architecture characterization. Extract semantic content only. "
            "Never invent provenance, source IDs, privacy scope, authority, permissions, "
            "confidence, validity windows, or lifecycle state; those are caller-owned. "
            "When the incoming statement is explicitly a correction, update the matching "
            "existing fact. When it is explicitly a separate conflicting claim and not a "
            "correction, keep the existing fact unchanged and add a separate fact."
        ),
        enable_inserts=True,
        enable_updates=True,
        enable_deletes=False,
    )


def validate_correction(existing: MemoryRecord, rows: list[dict], *, explicit_correction: bool) -> dict:
    if not explicit_correction:
        raise ValueError("Correction update requires caller-established explicit_correction")
    if len(rows) != 1 or rows[0]["id"] != MUSIC_ID:
        raise ValueError("Correction must update exactly the caller-selected existing memory")
    record = rows[0]
    if record["subject"] != "music-lesson":
        raise ValueError("Correction changed subject")
    statement = record["statement"].lower()
    if "thursday" not in statement or "17:00" not in statement or "wednesday" in statement:
        raise ValueError(f"Correction proposal has wrong semantic result: {record['statement']}")
    if existing.subject != record["subject"]:
        raise ValueError("Correction target mismatch")
    return record


def validate_noncorrection_conflict(existing: MemoryRecord, rows: list[dict], *, explicit_correction: bool) -> dict:
    if explicit_correction:
        raise ValueError("Conflict fixture must not be marked correction")
    by_id = {row["id"]: row for row in rows}
    prior = by_id.get(PICKUP_ID)
    if prior is None:
        raise ValueError("Proposal silently dropped existing conflicting claim")
    if prior["statement"] != existing.statement or prior["subject"] != existing.subject:
        raise ValueError("Proposal silently overwrote existing conflicting claim")
    additions = [
        row for row in rows
        if row["id"] != PICKUP_ID
        and row["subject"] == "pickup-time"
        and "17:00" in row["statement"]
    ]
    if len(additions) != 1:
        raise ValueError("Proposal did not preserve one separate 17:00 conflicting claim")
    return additions[0]


def assert_silent_overwrite_rejected(existing: MemoryRecord) -> str:
    fake = [{"id": PICKUP_ID, "kind": "fact", "subject": "pickup-time", "statement": "pickup is at 17:00"}]
    try:
        validate_noncorrection_conflict(existing, fake, explicit_correction=False)
    except ValueError as exc:
        return str(exc)
    raise RuntimeError("Deterministic validator accepted a silent conflict overwrite")


def mcp_text(result) -> str:
    data = getattr(result, "data", None)
    if data is not None:
        return data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str)
    blocks = getattr(result, "content", None) or []
    values = []
    for block in blocks:
        text = getattr(block, "text", None)
        values.append(text if text is not None else str(block))
    return "\n".join(values)


async def call_text(client: Client, name: str, arguments: dict) -> str:
    result = await client.call_tool(name=name, arguments=arguments)
    return mcp_text(result)


async def wait_search(
    client: Client,
    query: str,
    *,
    contains: str,
    absent: str | None = None,
    timeout: float = 45.0,
) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = await call_text(client, "search", {"query": query, "limit": 10})
        if contains in last and (absent is None or absent not in last):
            return last
        await asyncio.sleep(0.5)
    raise RuntimeError(
        f"ReMe search condition not reached: query={query!r} contains={contains!r} "
        f"absent={absent!r} last={last!r}"
    )


async def integration(args: argparse.Namespace) -> None:
    out = args.out
    workspace = args.workspace
    out.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    music_path = workspace / "digest/personal/music-lesson.md"
    pickup_16_path = workspace / "digest/personal/pickup-16.md"
    pickup_17_path = workspace / "digest/personal/pickup-17.md"

    initial_music = MemoryRecord(kind="fact", subject="music-lesson", statement="music lesson is Wednesday at 17:00")
    initial_pickup = MemoryRecord(kind="fact", subject="pickup-time", statement="pickup is at 16:00")

    atomic_markdown(
        music_path,
        {
            "name": "Music lesson",
            "description": "Synthetic authoritative schedule fixture.",
            "subject": "music-lesson",
            "state": "confirmed",
            "confirmation_basis": "explicit_user",
            "source_refs": [SRC_WED],
        },
        f"# Music lesson\n\nCurrent: Wednesday at 17:00\n\nSource: {SRC_WED}\n\nIndex canary: {MARK_WED}",
    )
    atomic_markdown(
        pickup_16_path,
        {
            "name": "Pickup claim 16",
            "description": "Synthetic unresolved-conflict source claim.",
            "subject": "pickup-time",
            "state": "confirmed",
            "confirmation_basis": "explicit_user",
            "source_refs": [SRC_16],
        },
        f"# Pickup claim\n\nClaim: pickup is at 16:00\n\nSource: {SRC_16}\n\nIndex canary: {MARK_16}",
    )

    os.environ["OLLAMA_MODEL_NAME"] = args.model
    os.environ["OLLAMA_HOST"] = args.ollama_host

    transport = StdioTransport(
        command=args.reme_python,
        args=[
            "-m",
            "reme.components.agent_wrapper.codex_mcp_server",
            "--config", str(args.config),
            "--workspace", str(workspace),
            "--job", "version",
            "--job", "status",
            "--job", "search",
            "--job", "read",
        ],
        cwd=str(args.repo_root),
    )

    evidence: dict = {
        "boundary": {
            "transport": "stdio-mcp",
            "authoritative_store": "Markdown/YAML",
            "reme_role": "read/search/index only",
            "langmem_role": "typed semantic proposal only",
            "model_schema_fields": list(MemoryRecord.model_fields),
            "caller_owned_fields": ["source_refs", "scope", "authority", "permission", "lifecycle"],
        },
        "result": "INCOMPLETE",
    }

    async with Client(transport, timeout=120) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools)
        evidence["boundary"]["exposed_reme_tools"] = names
        expected = ["read", "search", "status", "version"]
        if names != expected:
            raise RuntimeError(f"Unexpected ReMe stdio tool surface: expected {expected}, got {names}")
        if any(name in names for name in ("write", "edit", "move", "delete", "auto_memory", "auto_dream")):
            raise RuntimeError(f"Mutating/model-writing ReMe tool exposed: {names}")
        write_json(out / "integration.json", evidence)

        evidence["reme_version"] = await call_text(client, "version", {})
        evidence["initial_search"] = await wait_search(client, MARK_WED, contains=MARK_WED)

        mem_manager = manager(args.model, args.ollama_host)

        correction_items = await asyncio.to_thread(
            mem_manager.invoke,
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Explicit correction: not Wednesday. The music lesson is Thursday at 17:00.",
                    }
                ],
                "existing": [(MUSIC_ID, initial_music)],
            },
        )
        correction_rows = proposal_rows(correction_items)
        evidence["correction"] = {"proposal": correction_rows, "validated": False}
        write_json(out / "integration.json", evidence)
        accepted_correction = validate_correction(initial_music, correction_rows, explicit_correction=True)
        proposal_blob = json.dumps(correction_rows, ensure_ascii=False)
        if SRC_WED in proposal_blob or SRC_THU in proposal_blob:
            raise RuntimeError("LangMem proposal unexpectedly contains caller-owned source references")

        evidence["correction"] = {
            "proposal": correction_rows,
            "validated": True,
            "caller_source_refs": [SRC_WED, SRC_THU],
            "accepted_record": accepted_correction,
        }

        atomic_markdown(
            music_path,
            {
                "name": "Music lesson",
                "description": "Synthetic authoritative schedule fixture.",
                "subject": "music-lesson",
                "state": "confirmed",
                "confirmation_basis": "explicit_user",
                "source_refs": [SRC_WED, SRC_THU],
                "superseded": [{"statement": initial_music.statement, "source_ref": SRC_WED}],
            },
            (
                "# Music lesson\n\n"
                "Current: Thursday at 17:00\n\n"
                "Previous (superseded): Wednesday at 17:00\n\n"
                f"Sources: {SRC_WED}, {SRC_THU}\n\n"
                f"Index canary: {MARK_THU}"
            ),
        )
        evidence["corrected_search"] = await wait_search(client, MARK_THU, contains=MARK_THU)

        conflict_items = await asyncio.to_thread(
            mem_manager.invoke,
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Separate explicit claim, not a correction: pickup is at 17:00.",
                    }
                ],
                "existing": [(PICKUP_ID, initial_pickup)],
            },
        )
        conflict_rows = proposal_rows(conflict_items)
        evidence["conflict"] = {"proposal": conflict_rows, "validated": False}
        write_json(out / "integration.json", evidence)
        accepted_new_claim = validate_noncorrection_conflict(
            initial_pickup,
            conflict_rows,
            explicit_correction=False,
        )
        conflict_blob = json.dumps(conflict_rows, ensure_ascii=False)
        if SRC_16 in conflict_blob or SRC_17 in conflict_blob:
            raise RuntimeError("LangMem conflict proposal unexpectedly contains caller-owned source references")

        rejected_reason = assert_silent_overwrite_rejected(initial_pickup)
        evidence["conflict"] = {
            "proposal": conflict_rows,
            "validated": True,
            "existing_preserved": True,
            "accepted_new_claim": accepted_new_claim,
            "caller_source_refs": [SRC_16, SRC_17],
            "synthetic_silent_overwrite_rejected": True,
            "rejection_reason": rejected_reason,
        }

        # Ada owns lifecycle state and writes both explicit claims as contradicted.
        for path, name, claim, source_ref, marker in (
            (pickup_16_path, "Pickup claim 16", "pickup is at 16:00", SRC_16, MARK_16),
            (pickup_17_path, "Pickup claim 17", "pickup is at 17:00", SRC_17, MARK_17),
        ):
            atomic_markdown(
                path,
                {
                    "name": name,
                    "description": "Synthetic unresolved-conflict source claim.",
                    "subject": "pickup-time",
                    "state": "contradicted",
                    "confirmation_basis": "explicit_user",
                    "source_refs": [source_ref],
                },
                f"# Pickup claim\n\nClaim: {claim}\n\nSource: {source_ref}\n\nIndex canary: {marker}",
            )

        evidence["conflict_search_16"] = await wait_search(client, MARK_16, contains=MARK_16)
        evidence["conflict_search_17"] = await wait_search(client, MARK_17, contains=MARK_17)

        # Out-of-band edit is authoritative. ReMe must re-index it without any
        # LangMem or ReMe model-mediated write.
        text = music_path.read_text(encoding="utf-8")
        text = text.replace("Current: Thursday at 17:00", "Current: Friday at 17:00")
        text = text.replace(MARK_THU, MARK_FRI)
        music_path.write_text(text, encoding="utf-8")
        evidence["outside_edit_search"] = await wait_search(
            client,
            MARK_FRI,
            contains=MARK_FRI,
            absent=MARK_THU,
        )
        evidence["outside_edit_read"] = await call_text(
            client,
            "read",
            {"path": "digest/personal/music-lesson.md", "start_line": 1, "end_line": 80},
        )
        if "Current: Friday at 17:00" not in evidence["outside_edit_read"]:
            raise RuntimeError("ReMe read did not return authoritative out-of-band edit")

        evidence["status"] = await call_text(client, "status", {})

    evidence["result"] = "PASS"
    write_json(out / "integration.json", evidence)


def summarize(result_dir: Path) -> None:
    steps = []
    step_file = result_dir / "steps.tsv"
    if step_file.exists():
        for line in step_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            name, status, seconds = line.split("\t", 2)
            steps.append({"name": name, "status": status, "seconds": seconds})

    overall = "PASS" if steps and all(x["status"] == "PASS" for x in steps if x["name"] != "pip-audit") else "FINDINGS"
    audit = result_dir / "pip-audit.json"
    audit_status = "not-run"
    audit_vulns = None
    if audit.exists():
        try:
            data = json.loads(audit.read_text(encoding="utf-8"))
            deps = data.get("dependencies", []) if isinstance(data, dict) else []
            audit_vulns = sum(len(x.get("vulns", [])) for x in deps if isinstance(x, dict))
            audit_status = "pass" if audit_vulns == 0 else "finding"
        except Exception as exc:
            audit_status = f"unreadable: {exc}"

    inventory_path = result_dir / "inventory.json"
    inv = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else {}
    summary = {
        "overall": overall,
        "steps": steps,
        "runtime_distribution_count": inv.get("distribution_count"),
        "security_floor_checks": inv.get("security_floor_checks"),
        "manual_license_review_count": len(inv.get("manual_license_review", [])),
        "pip_audit_status": audit_status,
        "pip_audit_vulnerability_count": audit_vulns,
    }
    write_json(result_dir / "summary.json", summary)

    lines = [
        "# ReMe + LangMem final characterization",
        "",
        f"Overall core run: **{overall}**",
        "",
        "| Step | Status | Seconds |",
        "| --- | --- | ---: |",
    ]
    for row in steps:
        lines.append(f"| {row['name']} | {row['status']} | {row['seconds']} |")
    lines += [
        "",
        f"- Runtime distributions: {summary['runtime_distribution_count']}",
        f"- Security floors: {summary['security_floor_checks']}",
        f"- Packages requiring manual license-metadata review: {summary['manual_license_review_count']}",
        f"- pip-audit: {audit_status} ({audit_vulns} vulnerability record(s))",
        "",
        "A pip-audit failure or unknown license metadata is a review finding, not automatically a framework rejection.",
    ]
    (result_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    bundle_parts = [
        "# ReMe + LangMem final review bundle",
        "",
        (result_dir / "SUMMARY.md").read_text(encoding="utf-8"),
    ]
    for filename in (
        "environment.txt",
        "footprint.txt",
        "pip-freeze.txt",
        "inventory.json",
        "integration/integration.json",
        "logs/integration.log",
        "pip-audit.json",
        "pip-audit.log",
    ):
        path = result_dir / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if filename == "logs/integration.log":
            text = "\n".join(text.splitlines()[-100:])
        if filename == "inventory.json":
            try:
                data = json.loads(text)
                compact = {
                    "distribution_count": data.get("distribution_count"),
                    "selected_versions": data.get("selected_versions"),
                    "security_floor_checks": data.get("security_floor_checks"),
                    "manual_license_review": data.get("manual_license_review"),
                }
                text = json.dumps(compact, indent=2, ensure_ascii=False)
            except Exception:
                pass
        bundle_parts += ["", f"===== {filename} =====", text]

    (result_dir / "REVIEW-BUNDLE.txt").write_text("\n".join(bundle_parts) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inventory")
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=lambda a: inventory(a.out))

    p = sub.add_parser("integration")
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--reme-python", required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--ollama-host", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=lambda a: asyncio.run(integration(a)))

    p = sub.add_parser("summary")
    p.add_argument("--result-dir", type=Path, required=True)
    p.set_defaults(func=lambda a: summarize(a.result_dir))

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
