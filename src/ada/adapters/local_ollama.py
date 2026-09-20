from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.providers.ollama import OllamaProvider

from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.personality import ADA_PERSONALITY_INSTRUCTIONS


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"


class LocalModelConfigurationError(ValueError):
    """The local model profile violates Ada's local-only assumptions."""


@dataclass(frozen=True, slots=True)
class LocalOllamaConfig:
    model: str = DEFAULT_OLLAMA_MODEL
    base_url: str = DEFAULT_OLLAMA_BASE_URL


def validate_local_ollama_base_url(base_url: str) -> None:
    """Require the first local-chat profile to use a loopback Ollama endpoint."""

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise LocalModelConfigurationError(
            "Ollama URL must use http or https"
        )

    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise LocalModelConfigurationError(
            "Ada local chat only accepts a loopback Ollama endpoint"
        )

    if parsed.path.rstrip("/") != "/v1":
        raise LocalModelConfigurationError(
            "Ollama URL must point to the OpenAI-compatible /v1 endpoint"
        )


def build_local_ollama_runtime(
    config: LocalOllamaConfig = LocalOllamaConfig(),
) -> PydanticAIRuntime:
    """Construct the first local-only PydanticAI/Ollama chat runtime."""

    validate_local_ollama_base_url(config.base_url)

    provider = OllamaProvider(base_url=config.base_url)
    model = OllamaModel(
        config.model,
        provider=provider,
        settings=OpenAIChatModelSettings(
            openai_reasoning_effort="none",
        ),
    )
    agent = Agent(
        model,
        instructions=ADA_PERSONALITY_INSTRUCTIONS,
    )
    return PydanticAIRuntime(
        agent,
        keep_session_history=True,
    )
