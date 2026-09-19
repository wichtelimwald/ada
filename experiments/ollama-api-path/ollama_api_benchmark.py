from __future__ import annotations

import json
import statistics
import time
import urllib.request
from typing import Any

BASE = "http://localhost:11434"
MODEL = "ada-qwen3-8b-4k"
RUNS = 3
PROMPT = (
    "Check 2026-09-21 for calendar conflicts. "
    "You must use the calendar_conflicts tool exactly once. "
    "Then answer in one short sentence."
)

TOOL_RESULT = (
    "15:00 school appointment conflicts with 15:15 music lesson "
    "after 25 minutes travel"
)

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calendar_conflicts",
        "description": "Return known calendar conflicts for one ISO date.",
        "parameters": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string",
                    "description": "ISO date in YYYY-MM-DD format",
                }
            },
            "required": ["day"],
        },
    },
}


def post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def validate_args(raw: Any) -> bool:
    if isinstance(raw, str):
        raw = json.loads(raw)
    return isinstance(raw, dict) and raw.get("day") == "2026-09-21"


def native_once(label: str) -> dict[str, Any]:
    start = time.perf_counter()
    first = post(
        "/api/chat",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "tools": [TOOL_SCHEMA],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 256,
                "num_ctx": 4096,
            },
        },
    )
    assistant = first["message"]
    calls = assistant.get("tool_calls") or []
    valid_call = len(calls) == 1
    if valid_call:
        function = calls[0].get("function", {})
        valid_call = (
            function.get("name") == "calendar_conflicts"
            and validate_args(function.get("arguments"))
        )

    messages = [
        {"role": "user", "content": PROMPT},
        assistant,
        {"role": "tool", "content": TOOL_RESULT},
    ]
    second = post(
        "/api/chat",
        {
            "model": MODEL,
            "messages": messages,
            "tools": [TOOL_SCHEMA],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 256,
                "num_ctx": 4096,
            },
        },
    )
    elapsed = time.perf_counter() - start
    output = second["message"].get("content", "")
    return {
        "label": label,
        "elapsed_seconds": round(elapsed, 3),
        "tool_calls": len(calls),
        "output": output,
        "valid": valid_call and "25" in output,
    }


def openai_once(label: str) -> dict[str, Any]:
    start = time.perf_counter()
    first = post(
        "/v1/chat/completions",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "tools": [TOOL_SCHEMA],
            "stream": False,
            "temperature": 0,
            "max_tokens": 256,
            "reasoning_effort": "none",
        },
    )
    assistant = first["choices"][0]["message"]
    calls = assistant.get("tool_calls") or []
    valid_call = len(calls) == 1
    if valid_call:
        function = calls[0].get("function", {})
        valid_call = (
            function.get("name") == "calendar_conflicts"
            and validate_args(function.get("arguments"))
        )

    messages = [
        {"role": "user", "content": PROMPT},
        assistant,
        {
            "role": "tool",
            "tool_call_id": calls[0]["id"] if calls else "missing",
            "content": TOOL_RESULT,
        },
    ]
    second = post(
        "/v1/chat/completions",
        {
            "model": MODEL,
            "messages": messages,
            "tools": [TOOL_SCHEMA],
            "stream": False,
            "temperature": 0,
            "max_tokens": 256,
            "reasoning_effort": "none",
        },
    )
    elapsed = time.perf_counter() - start
    output = second["choices"][0]["message"].get("content", "")
    return {
        "label": label,
        "elapsed_seconds": round(elapsed, 3),
        "tool_calls": len(calls),
        "output": output,
        "valid": valid_call and "25" in output,
    }


def summarize(name: str, warmup: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    timings = [float(r["elapsed_seconds"]) for r in runs]
    return {
        "api": name,
        "warmup": warmup,
        "runs": runs,
        "mean_seconds": round(statistics.mean(timings), 3),
        "median_seconds": round(statistics.median(timings), 3),
        "all_valid": all(bool(r["valid"]) for r in runs),
    }


native_warmup = native_once("warmup")
openai_warmup = openai_once("warmup")

native_runs: list[dict[str, Any]] = []
openai_runs: list[dict[str, Any]] = []

for i in range(1, RUNS + 1):
    native_runs.append(native_once(f"run_{i}"))
    openai_runs.append(openai_once(f"run_{i}"))

summary = {
    "model": MODEL,
    "native": summarize("native /api/chat", native_warmup, native_runs),
    "openai_compatible": summarize(
        "openai-compatible /v1/chat/completions",
        openai_warmup,
        openai_runs,
    ),
}
print(json.dumps(summary, indent=2))
