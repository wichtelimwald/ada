from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RunContext,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai_harness import StepPersistence
from pydantic_ai_harness.step_persistence import (
    SqliteStepStore,
    annotate_tool_effect,
    continue_run,
)

CONVERSATION_ID = "ada-pydanticai-recovery-v1"
OPERATION_ID = "calendar-school-appointment-001"
TOOL_CALL_ID = "ada-calendar-create-001"
CRASH_EXIT_CODE = 86


class InjectedCrash(RuntimeError):
    """Simulate a process-visible failure after the provider committed."""


class ActionLedger:
    """Tiny Ada-owned ledger; authoritative for side-effect state in this probe."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    operation_id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, operation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT operation_id, action_type, status, provider_id FROM actions WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "operation_id": row[0],
            "action_type": row[1],
            "status": row[2],
            "provider_id": row[3],
        }

    def mark_executing(self, operation_id: str, action_type: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO actions(operation_id, action_type, status)
                VALUES (?, ?, 'executing')
                ON CONFLICT(operation_id) DO UPDATE SET
                    action_type = excluded.action_type,
                    status = CASE
                        WHEN actions.status = 'committed' THEN actions.status
                        ELSE 'executing'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (operation_id, action_type),
            )

    def mark_committed(self, operation_id: str, action_type: str, provider_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO actions(operation_id, action_type, status, provider_id)
                VALUES (?, ?, 'committed', ?)
                ON CONFLICT(operation_id) DO UPDATE SET
                    action_type = excluded.action_type,
                    status = 'committed',
                    provider_id = excluded.provider_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (operation_id, action_type, provider_id),
            )


class FakeCalendarProvider:
    """External system simulation with reconciliation metadata but no uniqueness guarantee."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    starts_at TEXT NOT NULL
                )
                """
            )

    def create(self, operation_id: str, title: str, starts_at: str) -> str:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events(operation_id, title, starts_at) VALUES (?, ?, ?)",
                (operation_id, title, starts_at),
            )
            provider_id = str(cursor.lastrowid)
        return provider_id

    def find_by_operation_id(self, operation_id: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT provider_id, operation_id, title, starts_at FROM events WHERE operation_id = ? ORDER BY provider_id",
                (operation_id,),
            ).fetchall()
        return [
            {
                "provider_id": str(row[0]),
                "operation_id": row[1],
                "title": row[2],
                "starts_at": row[3],
            }
            for row in rows
        ]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM events").fetchone()
        assert row is not None
        return int(row[0])


class AdaGuard:
    """Minimal deterministic authorization boundary for the probe."""

    @staticmethod
    def authorize_calendar_create(operation_id: str, title: str, starts_at: str) -> None:
        if operation_id != OPERATION_ID:
            raise PermissionError("unexpected operation id")
        if not title.strip() or not starts_at.strip():
            raise PermissionError("calendar action is incomplete")


@dataclass
class Deps:
    step_store: SqliteStepStore
    ledger: ActionLedger
    provider: FakeCalendarProvider
    crash_mode: str | None = None


def _has_committed_tool_result(messages: list[ModelMessage]) -> bool:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if not isinstance(part, ToolReturnPart):
                continue
            if part.tool_name != "create_calendar_event":
                continue
            content = part.content
            if isinstance(content, str) and content.startswith(
                ("created:", "reconciled:", "already_committed:")
            ):
                return True
    return False


def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    del info
    if _has_committed_tool_result(messages):
        return ModelResponse(parts=[TextPart("done")])
    return ModelResponse(
        parts=[
            ToolCallPart(
                "create_calendar_event",
                {
                    "operation_id": OPERATION_ID,
                    "title": "School appointment",
                    "starts_at": "2026-09-21T15:00:00+02:00",
                },
                tool_call_id=TOOL_CALL_ID,
            )
        ]
    )


def build_agent(store: SqliteStepStore) -> Agent[Deps, str]:
    agent: Agent[Deps, str] = Agent(
        FunctionModel(scripted_model),
        deps_type=Deps,
        capabilities=[StepPersistence(store=store, agent_name="ada-pydanticai-recovery")],
    )

    @agent.tool
    async def create_calendar_event(
        ctx: RunContext[Deps],
        operation_id: str,
        title: str,
        starts_at: str,
    ) -> str:
        """Create one calendar event through the deterministic Ada boundary."""
        AdaGuard.authorize_calendar_create(operation_id, title, starts_at)

        await annotate_tool_effect(
            ctx.deps.step_store,
            ctx,
            idempotency_key=operation_id,
            effect_summary=f"create calendar event {title!r} at {starts_at}",
        )

        action = ctx.deps.ledger.get(operation_id)
        if action is not None and action["status"] == "committed":
            return f"already_committed:{action['provider_id']}"

        existing = ctx.deps.provider.find_by_operation_id(operation_id)
        if len(existing) > 1:
            raise RuntimeError("provider contains duplicate events for one Ada operation id")
        if len(existing) == 1:
            provider_id = existing[0]["provider_id"]
            ctx.deps.ledger.mark_committed(operation_id, "calendar.create", provider_id)
            return f"reconciled:{provider_id}"

        ctx.deps.ledger.mark_executing(operation_id, "calendar.create")
        provider_id = ctx.deps.provider.create(operation_id, title, starts_at)

        if ctx.deps.crash_mode == "exception":
            raise InjectedCrash("injected after provider commit")
        if ctx.deps.crash_mode == "hard-exit":
            os._exit(CRASH_EXIT_CODE)

        ctx.deps.ledger.mark_committed(operation_id, "calendar.create", provider_id)
        return f"created:{provider_id}"

    return agent


def paths(workdir: Path) -> tuple[Path, Path, Path]:
    return (
        workdir / "step-persistence.db",
        workdir / "ada-actions.db",
        workdir / "fake-calendar.db",
    )


def make_deps(workdir: Path, crash_mode: str | None) -> tuple[SqliteStepStore, Deps]:
    step_path, ledger_path, provider_path = paths(workdir)
    store = SqliteStepStore(database=str(step_path))
    deps = Deps(
        step_store=store,
        ledger=ActionLedger(ledger_path),
        provider=FakeCalendarProvider(provider_path),
        crash_mode=crash_mode,
    )
    return store, deps


async def crash_once(workdir: Path, crash_mode: str) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    store, deps = make_deps(workdir, crash_mode)
    agent = build_agent(store)
    await agent.run(
        "Create the school appointment.",
        deps=deps,
        conversation_id=CONVERSATION_ID,
    )


async def inspect_state(workdir: Path) -> dict[str, Any]:
    store, deps = make_deps(workdir, None)
    runs = await store.list_runs(conversation_id=CONVERSATION_ID)
    latest_run_id = runs[-1].run_id if runs else None
    unresolved: list[Any] = []
    complete_snapshot_available = False
    interrupted_snapshot_available = False
    if latest_run_id is not None:
        unresolved = await store.list_unresolved_tool_effects(run_id=latest_run_id)
        try:
            await continue_run(store, run_id=latest_run_id)
            complete_snapshot_available = True
        except LookupError:
            pass
        try:
            await continue_run(store, run_id=latest_run_id, include_interrupted=True)
            interrupted_snapshot_available = True
        except LookupError:
            pass

    return {
        "latest_run_id": latest_run_id,
        "run_count": len(runs),
        "unresolved_tool_effects": [
            {
                "tool_name": item.tool_name,
                "tool_call_id": item.tool_call_id,
                "idempotency_key": item.idempotency_key,
                "status": item.status,
            }
            for item in unresolved
        ],
        "complete_snapshot_available": complete_snapshot_available,
        "interrupted_snapshot_available": interrupted_snapshot_available,
        "provider_event_count": deps.provider.count(),
        "action": deps.ledger.get(OPERATION_ID),
    }


async def recover(workdir: Path) -> dict[str, Any]:
    store, deps = make_deps(workdir, None)
    runs = await store.list_runs(conversation_id=CONVERSATION_ID)
    if not runs:
        raise RuntimeError("no persisted run found")
    failed_run_id = runs[-1].run_id

    try:
        history = await continue_run(store, run_id=failed_run_id, include_interrupted=True)
        resume_source = "step-persistence"
    except LookupError:
        history = None
        resume_source = "fresh-run-after-noncontinuable-crash"

    agent = build_agent(store)
    result = await agent.run(
        "Resume the interrupted calendar action safely.",
        deps=deps,
        message_history=history,
        conversation_id=CONVERSATION_ID,
    )

    final_state = await inspect_state(workdir)
    final_state.update(
        {
            "resume_source": resume_source,
            "agent_output": result.output,
            "duplicate_side_effect": deps.provider.count() != 1,
        }
    )
    return final_state


def run_child(workdir: Path, crash_mode: str) -> int:
    completed = subprocess.run(
        [
            sys.executable,
            __file__,
            "crash",
            "--workdir",
            str(workdir),
            "--crash-mode",
            crash_mode,
        ],
        check=False,
    )
    return completed.returncode


async def run_scenario(root: Path, crash_mode: str) -> dict[str, Any]:
    workdir = root / crash_mode
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    exit_code = run_child(workdir, crash_mode)
    before = await inspect_state(workdir)
    after = await recover(workdir)

    return {
        "crash_mode": crash_mode,
        "exit_code": exit_code,
        "before_recovery": before,
        "after_recovery": after,
        "safe": (
            before["provider_event_count"] == 1
            and after["provider_event_count"] == 1
            and after["action"] is not None
            and after["action"]["status"] == "committed"
            and not after["duplicate_side_effect"]
        ),
    }


async def run_all(root: Path) -> int:
    root.mkdir(parents=True, exist_ok=True)
    scenarios = [
        await run_scenario(root, "exception"),
        await run_scenario(root, "hard-exit"),
    ]
    summary = {
        "pydanticai_recovery_probe": scenarios,
        "all_safe": all(item["safe"] for item in scenarios),
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["all_safe"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["all", "crash", "inspect", "recover"])
    parser.add_argument("--workdir", type=Path, default=Path(".probe-state"))
    parser.add_argument(
        "--crash-mode",
        choices=["exception", "hard-exit"],
        default="exception",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "all":
        return asyncio.run(run_all(args.workdir))
    if args.command == "crash":
        asyncio.run(crash_once(args.workdir, args.crash_mode))
        return 0
    if args.command == "inspect":
        print(json.dumps(asyncio.run(inspect_state(args.workdir)), indent=2, default=str))
        return 0
    if args.command == "recover":
        print(json.dumps(asyncio.run(recover(args.workdir)), indent=2, default=str))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
