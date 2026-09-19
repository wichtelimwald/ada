from __future__ import annotations

import os
import time

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

MODEL = os.environ.get("ADA_OLLAMA_MODEL", "ada-qwen3-8b-4k")
BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434/v1",
)

model = OllamaModel(
    MODEL,
    provider=OllamaProvider(base_url=BASE_URL),
)
Agent(
    model,
    model_settings=OpenAIChatModelSettings(
        temperature=0.0,
        max_tokens=256,
        openai_reasoning_effort="none",
    ),
)

print("idle_probe_ready", flush=True)
time.sleep(600)
