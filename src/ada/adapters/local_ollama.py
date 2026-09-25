from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

import httpx2
import pydantic_ai
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.providers.ollama import OllamaProvider

from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.bootstrap.personality import load_bootstrap_personality
from ada.core.actions import CreateCalendarEventDraft
from ada.ports.agent_runtime import AgentTextReply
from ada.core.personality import (
    PersonalityProfile,
    render_personality_instructions,
)


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3.5:9b"


class LocalModelConfigurationError(ValueError):
    """The local model profile violates Ada's local-only assumptions."""


class LocalModelUnavailableError(RuntimeError):
    """The configured loopback Ollama service/model is not ready."""


class _RejectRedirects(HTTPRedirectHandler):
    """Do not follow a local service redirect out of the loopback boundary."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


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
        # URL validation alone is insufficient: urllib otherwise honors host
        # proxy settings even for localhost when no bypass is configured.
        with build_opener(ProxyHandler({}), _RejectRedirects()).open(
            tags_url, timeout=timeout_seconds
        ) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError) as exc:
        if isinstance(exc, HTTPError):
            # Rejected redirects are HTTPError responses with an open body.
            exc.close()
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

    Callers may still omit personality for the unprotected development fallback
    and use the distribution bootstrap seed. When a file-native development
    Memory root is explicitly configured, the application layer bootstraps/loads
    the profile there and passes it here. Protected household Memory remains
    gated on the Memory Broker and protection-domain work.
    """

    validate_local_ollama_base_url(config.base_url)
    active_personality = personality or load_bootstrap_personality()

    # Ada owns its user-facing CLI output; suppress PydanticAI's first-run
    # observability banner for this product surface.
    pydantic_ai.BANNER_ENABLED = False

    instructions = render_personality_instructions(active_personality) + """

For ordinary conversation, return an AgentTextReply.

When the user asks to create or add a calendar event, return a typed
CreateCalendarEventDraft, even when details are missing. A draft is intentionally
non-executable.

Do not invent material details. In particular:
- do not invent a year when the user gives only a day/month;
- do not invent an end time or duration;
- do not invent a location;
- set missing fields to null;
- in "unresolved", use only these canonical values when applicable:
  "title", "year", "date", "start_time", "end_time", "calendar";
- use language="de" for German requests and language="en" for English requests;
- use calendar_id="family" only when the user explicitly refers to the family
  calendar / Familienkalender.

For date, use YYYY-MM-DD only when the year is explicitly known from the user's
request. Otherwise preserve the user's partial date text and mark "year" unresolved.
For times, use HH:MM only when explicitly given.

Never claim that a calendar event was created, added, changed, or saved. You have
no direct calendar/provider authority. A draft is not permission and not proof of
execution.
""".rstrip()

    # The model call must use the same direct-transport rule as readiness.
    # Passing a client also prevents PydanticAI from creating an ambient
    # proxy-aware default client for later requests.
    http_client = httpx2.AsyncClient(trust_env=False, timeout=600.0)
    try:
        provider = OllamaProvider(
            base_url=config.base_url,
            http_client=http_client,
        )
        model = OllamaModel(
            config.model,
            provider=provider,
            settings=OpenAIChatModelSettings(
                openai_reasoning_effort="none",
            ),
        )
        agent = Agent(
            model,
            instructions=instructions,
            output_type=NativeOutput(
                [AgentTextReply, CreateCalendarEventDraft],
                name="ada_local_response",
                description=(
                    "Return either a conversational reply or a non-executable "
                    "calendar draft."
                ),
            ),
        )
        return PydanticAIRuntime(
            agent,
            keep_session_history=True,
            close_callback=http_client.aclose,
        )
    except BaseException:
        asyncio.run(http_client.aclose())
        raise
