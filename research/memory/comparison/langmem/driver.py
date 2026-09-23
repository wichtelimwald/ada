#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langmem import create_memory_manager

fixtures = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
model_name = sys.argv[3]
ollama_host = sys.argv[4]


class MemoryRecord(BaseModel):
    kind: Literal["preference", "fact"]
    subject: str = Field(description="Short neutral subject such as communication-style, music-lesson, or pickup-time")
    statement: str = Field(description="The factual or preference statement. Preserve unresolved alternatives rather than inventing a resolution.")
    evidence: list[str] = Field(default_factory=list, description="Evidence/source tokens copied verbatim when present")


model = ChatOllama(model=model_name, base_url=ollama_host, reasoning=False, temperature=0, num_predict=2048, keep_alive="10m")
manager = create_memory_manager(
    model,
    schemas=[MemoryRecord],
    instructions=(
        fixtures["instructions"]
        + " Extract only the synthetic preference/facts supplied. Keep atomic records. "
          "When the user explicitly corrects an existing fact, update that fact. "
          "When a conflicting new claim says it is not a correction, do not silently erase either claim."
    ),
    enable_inserts=True,
    enable_updates=True,
    enable_deletes=False,
)


def dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [dump(x) for x in obj]
    if isinstance(obj, tuple):
        return [dump(x) for x in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    return str(obj)


def run(text, existing=None):
    inp = {"messages": [{"role": "user", "content": text}]}
    if existing is not None:
        inp["existing"] = existing
    return manager.invoke(inp)


pref = run(fixtures["preference"])
corr_before = run(fixtures["correction_before"])
corr_after = run(fixtures["correction_after"], corr_before)
conf_a = run(fixtures["conflict_a"])
conf_b = run(fixtures["conflict_b"], conf_a)

result = {
    "preference": dump(pref),
    "correction_before": dump(corr_before),
    "correction_after": dump(corr_after),
    "conflict_a": dump(conf_a),
    "conflict_after_b": dump(conf_b),
}
(out / "semantic.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
