from __future__ import annotations

import json
import os
import statistics
import time

from openjarvis.agents.orchestrator import OrchestratorAgent
from openjarvis.core.types import ToolResult
from openjarvis.engine.ollama import OllamaEngine
from openjarvis.tools._stubs import BaseTool, ToolSpec

MODEL = os.environ.get("ADA_OLLAMA_MODEL", "ada-qwen3-8b-4k")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MEASURED_RUNS = 3

os.environ.setdefault("JARVIS_NUM_CTX", "4096")

tool_calls = 0


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
        global tool_calls
        tool_calls += 1
        day = str(params.get("day", ""))
        content = (
            "15:00 school appointment conflicts with 15:15 music lesson "
            "after 25 minutes travel"
            if day == "2026-09-21"
            else "no conflicts"
        )
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
    max_turns=3,
    temperature=0.0,
    max_tokens=256,
    parallel_tools=False,
)

PROMPT = (
    "Check 2026-09-21 for calendar conflicts. "
    "You must use the calendar_conflicts tool exactly once. "
    "Then answer in one short sentence."
)


def run_once(label: str) -> dict[str, object]:
    global tool_calls
    tool_calls = 0
    start = time.perf_counter()
    result = agent.run(PROMPT)
    elapsed = time.perf_counter() - start
    return {
        "label": label,
        "elapsed_seconds": round(elapsed, 3),
        "tool_calls": tool_calls,
        "turns": result.turns,
        "output": result.content,
        "valid": tool_calls == 1 and "25" in result.content,
    }


warmup = run_once("warmup")
runs = [run_once(f"run_{i}") for i in range(1, MEASURED_RUNS + 1)]
timings = [float(item["elapsed_seconds"]) for item in runs]

summary = {
    "framework": "OpenJarvis",
    "model": MODEL,
    "num_ctx": int(os.environ["JARVIS_NUM_CTX"]),
    "temperature": 0.0,
    "max_tokens": 256,
    "warmup": warmup,
    "runs": runs,
    "mean_seconds": round(statistics.mean(timings), 3),
    "median_seconds": round(statistics.median(timings), 3),
    "all_valid": all(bool(item["valid"]) for item in runs),
}
print(json.dumps(summary, indent=2))
