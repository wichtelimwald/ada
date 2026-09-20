from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.error import URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

import pydantic_ai
from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.providers.ollama import OllamaProvider

from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.bootstrap.personality import load_bootstrap_personality
from ada.core.actions import CreateCalendarEventProposal
from ada.core.personality import (
    PersonalityProfile,
    render_personality_instructions,
)


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"


class LocalModelConfigurationError(ValueError):
    """The local model profile violates Ada's local-only assumptions."""


class LocalModelUnavailableError(RuntimeError):
    """The configured loopback Ollama service/model is not ready."""


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


def check_local_ollama_ready(
    config: LocalOllamaConfig,
    *,
    timeout_seconds: float = 2.0,
) -> None:
    """Fail early with a concise error when the local service/model is unavailable."""

    validate_local_ollama_base_url(config.base_url)
    parsed = urlparse(config.base_url)
    tags_url = urlunparse(
        parsed._replace(
            path="/api/tags",
            params="",
            query="",
            fragment="",
        )
    )

    try:
        with urlopen(tags_url, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError) as exc:
        raise LocalModelUnavailableError(
            f"cannot reach local Ollama at {parsed.scheme}://{parsed.netloc}"
        ) from exc

    installed = {
        str(model.get("name") or model.get("model"))
        for model in payload.get("models", ())
        if isinstance(model, dict) and (model.get("name") or model.get("model"))
    }
    if config.model not in installed:
        raise LocalModelUnavailableError(
            f"local Ollama model {config.model!r} is not installed; "
            f"run: ollama pull {config.model}"
        )


def build_local_ollama_runtime(
    config: LocalOllamaConfig = LocalOllamaConfig(),
    *,
    personality: PersonalityProfile | None = None,
) -> PydanticAIRuntime:
    """Construct the first local-only PydanticAI/Ollama chat runtime.

    Until the authoritative Memory adapter exists, callers may omit personality
    and use the distribution bootstrap seed. Once Memory is implemented, the
    application layer must resolve/bootstrap the profile from Memory and pass it
    here explicitly.
    """

    validate_local_ollama_base_url(config.base_url)
    active_personality = personality or load_bootstrap_personality()

    # Ada owns its user-facing CLI output; suppress PydanticAI's first-run
    # observability banner for this product surface.
    pydantic_ai.BANNER_ENABLED = False

    provider = OllamaProvider(base_url=config.base_url)
    model = OllamaModel(
        config.model,
        provider=provider,
        settings=OpenAIChatModelSettings(
            openai_reasoning_effort="none",
        ),
    )
    instructions = render_personality_instructions(active_personality) + """

For ordinary conversation, return normal text.

When the user asks to create or add a calendar event, do not claim it happened.
Instead, return a typed CreateCalendarEventProposal only when the material event
details are sufficiently clear. If material details are missing or contradictory,
ask a concise clarification in normal text.

You have no direct calendar/provider authority. A proposal is not permission and
is not proof of execution.
""".rstrip()

    agent = Agent(
        model,
        instructions=instructions,
        output_type=[str, CreateCalendarEventProposal],
    )
    return PydanticAIRuntime(
        agent,
        keep_session_history=True,
    )
