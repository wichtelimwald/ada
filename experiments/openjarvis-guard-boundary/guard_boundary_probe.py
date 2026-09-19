from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from openjarvis.agents.native_openhands import NativeOpenHandsAgent
from openjarvis.core.config import AnalyticsConfig
from openjarvis.core.types import ToolCall, ToolResult
from openjarvis.mcp.protocol import MCPRequest
from openjarvis.mcp.server import MCPServer
from openjarvis.scheduler.scheduler import ScheduledTask, TaskScheduler
from openjarvis.scheduler.store import SchedulerStore
from openjarvis.security.runtime import execute_secured_tool
from openjarvis.tools._stubs import BaseTool, ToolExecutor, ToolSpec

TOOL_NAME = "ada_calendar_create"


@dataclass
class ProbeState:
    allowed: bool
    guard_checks: int = 0
    provider_writes: int = 0


class AdaGuard:
    """Tiny deterministic Ada-owned authorization boundary."""

    def __init__(self, state: ProbeState) -> None:
        self.state = state

    def authorize(self, action: str) -> None:
        self.state.guard_checks += 1
        if action != "calendar.create":
            raise PermissionError(f"unexpected action: {action}")
        if not self.state.allowed:
            raise PermissionError("Ada Guard denied calendar.create")


class GuardedCalendarTool(BaseTool):
    """Only this adapter is allowed to mutate the fake provider."""

    tool_id = TOOL_NAME

    def __init__(self, state: ProbeState) -> None:
        self.state = state
        self.guard = AdaGuard(state)

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=TOOL_NAME,
            description="Create a fake calendar event through Ada Guard.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                },
                "required": ["title"],
            },
        )

    def execute(self, **params: Any) -> ToolResult:
        self.guard.authorize("calendar.create")
        title = str(params.get("title", "")).strip()
        if not title:
            return ToolResult(
                tool_name=TOOL_NAME,
                content="missing title",
                success=False,
            )
        self.state.provider_writes += 1
        return ToolResult(
            tool_name=TOOL_NAME,
            content=f"created:{title}",
            success=True,
        )


def engine_response(content: str | None, **extra: Any) -> dict[str, Any]:
    response: dict[str, Any] = {
        "content": content,
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        "model": "probe-model",
        "finish_reason": "stop",
    }
    response.update(extra)
    return response


def make_agent(tool: BaseTool) -> NativeOpenHandsAgent:
    engine = MagicMock()
    engine.engine_id = "ada-probe"
    engine.generate.side_effect = [
        engine_response(
            None,
            tool_calls=[
                {
                    "id": "call-1",
                    "name": TOOL_NAME,
                    "arguments": json.dumps({"title": "School appointment"}),
                }
            ],
        ),
        engine_response("done"),
    ]
    return NativeOpenHandsAgent(
        engine,
        "probe-model",
        tools=[tool],
    )


def path_tool_executor(state: ProbeState) -> dict[str, Any]:
    tool = GuardedCalendarTool(state)
    result = ToolExecutor([tool]).execute(
        ToolCall(
            id="direct-1",
            name=TOOL_NAME,
            arguments=json.dumps({"title": "School appointment"}),
        )
    )
    return {"framework_success": result.success, "content": result.content}


def path_mcp(state: ProbeState) -> dict[str, Any]:
    tool = GuardedCalendarTool(state)
    server = MCPServer(tools=[tool])

    listed = server.handle(MCPRequest(method="tools/list", id=1))
    exposed = [item["name"] for item in listed.result["tools"]]

    response = server.handle(
        MCPRequest(
            method="tools/call",
            id=2,
            params={
                "name": TOOL_NAME,
                "arguments": {"title": "School appointment"},
            },
        )
    )
    result = response.result or {}
    return {
        "framework_success": response.error is None and not bool(result.get("isError")),
        "error": response.error,
        "exposed_tools": exposed,
        "only_explicit_tool_exposed": exposed == [TOOL_NAME],
    }


def path_agent(state: ProbeState) -> dict[str, Any]:
    tool = GuardedCalendarTool(state)
    agent = make_agent(tool)
    result = agent.run("Create the school appointment.")
    return {
        "framework_success": True,
        "agent_output": result.content,
        "tool_results": [
            {
                "success": item.success,
                "content": item.content,
            }
            for item in result.tool_results
        ],
    }


class SchedulerSystem:
    """Small adapter so TaskScheduler invokes a real OpenJarvis agent."""

    def __init__(self, state: ProbeState) -> None:
        self.state = state
        self.seen_tools: list[str] | None = None

    def ask(
        self,
        prompt: str,
        *,
        agent: str | None = None,
        tools: list[str] | None = None,
        **_: Any,
    ) -> str:
        self.seen_tools = tools
        if tools != [TOOL_NAME]:
            raise RuntimeError(f"scheduler exposed unexpected tools: {tools!r}")
        real_agent = make_agent(GuardedCalendarTool(self.state))
        return real_agent.run(prompt).content


def path_scheduler(state: ProbeState) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ada-openjarvis-scheduler-") as tmp:
        store = SchedulerStore(Path(tmp) / "scheduler.db")
        system = SchedulerSystem(state)
        scheduler = TaskScheduler(store, system=system)
        task = ScheduledTask(
            id="ada-probe-task",
            prompt="Create the school appointment.",
            schedule_type="once",
            schedule_value="2099-01-01T00:00:00+00:00",
            agent="native_openhands",
            tools=TOOL_NAME,
        )
        store.save_task(task.to_dict())
        scheduler._execute_task(task)  # exact OpenJarvis execution method under test
        return {
            "framework_success": True,
            "tools_forwarded": system.seen_tools,
            "only_explicit_tool_exposed": system.seen_tools == [TOOL_NAME],
        }


def path_server_direct(state: ProbeState) -> dict[str, Any]:
    result = execute_secured_tool(
        GuardedCalendarTool(state),
        {"title": "School appointment"},
        agent_id="server:api",
    )
    return {"framework_success": result.success, "content": result.content}


PATHS = {
    "tool_executor": path_tool_executor,
    "mcp": path_mcp,
    "agent": path_agent,
    "scheduler": path_scheduler,
    "server_direct_helper": path_server_direct,
}


def run_case(name: str, fn: Any, allowed: bool) -> dict[str, Any]:
    state = ProbeState(allowed=allowed)
    details = fn(state)
    expected_writes = 1 if allowed else 0
    passed = state.guard_checks == 1 and state.provider_writes == expected_writes
    if "only_explicit_tool_exposed" in details:
        passed = passed and bool(details["only_explicit_tool_exposed"])
    return {
        "path": name,
        "allowed": allowed,
        "guard_checks": state.guard_checks,
        "provider_writes": state.provider_writes,
        "expected_provider_writes": expected_writes,
        "passed": passed,
        "details": details,
    }


def main() -> int:
    results: list[dict[str, Any]] = []
    for name, fn in PATHS.items():
        results.append(run_case(name, fn, True))
        results.append(run_case(name, fn, False))

    summary = {
        "openjarvis_guard_boundary_probe": results,
        "analytics_enabled_default": AnalyticsConfig().enabled,
        "all_passed": all(item["passed"] for item in results),
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
