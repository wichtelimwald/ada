from __future__ import annotations

import json
import os
import statistics
import time

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

MODEL = os.environ.get("ADA_OLLAMA_MODEL", "ada-qwen3-8b-4k")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MEASURED_RUNS = 3

tool_calls = 0

model = OllamaModel(
    MODEL,
    provider=OllamaProvider(base_url=BASE_URL),
)
agent = Agent(
    model,
    model_settings=OpenAIChatModelSettings(
        temperature=0.0,
        max_tokens=256,
        openai_reasoning_effort="none",
    ),
)


@agent.tool_plain
def calendar_conflicts(day: str) -> str:
    """Return known calendar conflicts for one ISO date."""
    global tool_calls
    tool_calls += 1
    if day == "2026-09-21":
        return (
            "15:00 school appointment conflicts with 15:15 music lesson "
            "after 25 minutes travel"
        )
    return "no conflicts"


PROMPT = (
    "Check 2026-09-21 for calendar conflicts. "
    "You must use the calendar_conflicts tool exactly once. "
    "Then answer in one short sentence."
)


def run_once(label: str) -> dict[str, object]:
    global tool_calls
    tool_calls = 0
    start = time.perf_counter()
    result = agent.run_sync(PROMPT)
    elapsed = time.perf_counter() - start
    return {
        "label": label,
        "elapsed_seconds": round(elapsed, 3),
        "tool_calls": tool_calls,
        "output": result.output,
        "valid": tool_calls == 1 and "25" in result.output,
    }


warmup = run_once("warmup")
runs = [run_once(f"run_{i}") for i in range(1, MEASURED_RUNS + 1)]
timings = [float(item["elapsed_seconds"]) for item in runs]

summary = {
    "framework": "PydanticAI",
    "model": MODEL,
    "temperature": 0.0,
    "max_tokens": 256,
    "openai_reasoning_effort": "none",
    "warmup": warmup,
    "runs": runs,
    "mean_seconds": round(statistics.mean(timings), 3),
    "median_seconds": round(statistics.median(timings), 3),
    "all_valid": all(bool(item["valid"]) for item in runs),
}
print(json.dumps(summary, indent=2))
