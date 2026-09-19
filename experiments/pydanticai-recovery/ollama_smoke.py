from __future__ import annotations

import os
import time

from pydantic_ai import Agent

MODEL = os.environ.get("ADA_OLLAMA_MODEL")
if not MODEL:
    raise SystemExit(
        "Set ADA_OLLAMA_MODEL to an installed Ollama model that supports tools."
    )

agent = Agent(f"ollama:{MODEL}")


@agent.tool_plain
def calendar_conflicts(day: str) -> str:
    """Return known calendar conflicts for one ISO date."""
    if day == "2026-09-21":
        return (
            "15:00 school appointment conflicts with 15:15 music lesson "
            "after 25 minutes travel"
        )
    return "no conflicts"


start = time.perf_counter()
result = agent.run_sync(
    "Check 2026-09-21 for calendar conflicts. "
    "Use the calendar_conflicts tool and summarize the result."
)
elapsed = time.perf_counter() - start

print(result.output)
print(f"elapsed_seconds={elapsed:.3f}")
print(f"usage={result.usage()}")
