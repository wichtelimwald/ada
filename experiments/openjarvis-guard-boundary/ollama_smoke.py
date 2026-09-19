from __future__ import annotations

import os
import time

from openjarvis.agents.orchestrator import OrchestratorAgent
from openjarvis.core.types import ToolResult
from openjarvis.engine.ollama import OllamaEngine
from openjarvis.tools._stubs import BaseTool, ToolSpec

MODEL = os.environ.get("ADA_OLLAMA_MODEL", "qwen3:8b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class CalendarConflictsTool(BaseTool):
    tool_id = "calendar_conflicts"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="calendar_conflicts",
            description="Return known calendar conflicts for one ISO date.",
            parameters={
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "ISO date in YYYY-MM-DD format",
                    }
                },
                "required": ["day"],
            },
        )

    def execute(self, **params: object) -> ToolResult:
        day = str(params.get("day", ""))
        if day == "2026-09-21":
            content = (
                "15:00 school appointment conflicts with 15:15 music lesson "
                "after 25 minutes travel"
            )
        else:
            content = "no conflicts"
        return ToolResult(
            tool_name="calendar_conflicts",
            content=content,
            success=True,
        )


engine = OllamaEngine(host=OLLAMA_HOST)
agent = OrchestratorAgent(
    engine,
    model=MODEL,
    tools=[CalendarConflictsTool()],
    max_turns=4,
    parallel_tools=False,
)

prompt = (
    "Check 2026-09-21 for calendar conflicts. "
    "You must use the calendar_conflicts tool exactly once. "
    "Then answer in one short sentence."
)

start = time.perf_counter()
result = agent.run(prompt)
elapsed = time.perf_counter() - start

print("framework=OpenJarvis")
print(f"model={MODEL}")
print(f"output={result.content}")
print(f"elapsed_seconds={elapsed:.3f}")
print(f"turns={result.turns}")
print(
    "tool_results="
    + repr(
        [
            {
                "tool": item.tool_name,
                "success": item.success,
                "content": item.content,
            }
            for item in result.tool_results
        ]
    )
)
