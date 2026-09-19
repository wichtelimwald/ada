from __future__ import annotations

import os
import time

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

MODEL = os.environ.get("ADA_OLLAMA_MODEL", "qwen3:8b")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

model = OllamaModel(
    MODEL,
    provider=OllamaProvider(base_url=BASE_URL),
)
agent = Agent(model)


@agent.tool_plain
def calendar_conflicts(day: str) -> str:
    """Return known calendar conflicts for one ISO date."""
    if day == "2026-09-21":
        return (
            "15:00 school appointment conflicts with 15:15 music lesson "
            "after 25 minutes travel"
        )
    return "no conflicts"


prompt = (
    "Check 2026-09-21 for calendar conflicts. "
    "You must use the calendar_conflicts tool exactly once. "
    "Then answer in one short sentence."
)

start = time.perf_counter()
result = agent.run_sync(prompt)
elapsed = time.perf_counter() - start

print(f"framework=PydanticAI")
print(f"model={MODEL}")
print(f"output={result.output}")
print(f"elapsed_seconds={elapsed:.3f}")
print(f"usage={result.usage}")
