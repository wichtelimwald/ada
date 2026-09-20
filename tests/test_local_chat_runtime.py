from __future__ import annotations

import unittest
from typing import Any, Sequence
from unittest.mock import patch

import pydantic_ai

from ada.adapters.local_ollama import (
    LocalModelConfigurationError,
    LocalOllamaConfig,
    build_local_ollama_runtime,
    validate_local_ollama_base_url,
)
from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.agent_runtime import AgentRequest


class FakeRunResult:
    def __init__(self, output: str, messages: Sequence[Any]) -> None:
        self.output = output
        self._messages = tuple(messages)

    def all_messages(self) -> tuple[Any, ...]:
        return self._messages


class FakeHistoryAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...] | None]] = []

    def run_sync(
        self,
        prompt: str,
        *,
        message_history: Sequence[Any] | None = None,
    ) -> FakeRunResult:
        history = tuple(message_history) if message_history is not None else None
        self.calls.append((prompt, history))
        prior = tuple(message_history or ())
        messages = (*prior, f"user:{prompt}", f"assistant:{prompt}")
        return FakeRunResult(f"answer:{prompt}", messages)


class LocalChatRuntimeTests(unittest.TestCase):
    def test_pydantic_runtime_reuses_only_ephemeral_session_history(self) -> None:
        agent = FakeHistoryAgent()
        runtime = PydanticAIRuntime(
            agent,
            keep_session_history=True,
        )

        first = runtime.run(AgentRequest(text="first"))
        second = runtime.run(AgentRequest(text="second"))

        self.assertEqual(first.text, "answer:first")
        self.assertEqual(second.text, "answer:second")
        self.assertIsNone(agent.calls[0][1])
        self.assertEqual(
            agent.calls[1][1],
            ("user:first", "assistant:first"),
        )

        runtime.reset_session()
        runtime.run(AgentRequest(text="after reset"))
        self.assertIsNone(agent.calls[2][1])

    def test_local_runtime_configures_typed_calendar_proposal_output(self) -> None:
        captured: dict[str, Any] = {}

        class FakeProvider:
            def __init__(self, *, base_url: str) -> None:
                captured["base_url"] = base_url

        class FakeModel:
            def __init__(self, name: str, *, provider: Any, settings: Any) -> None:
                captured["model_name"] = name
                captured["provider"] = provider
                captured["settings"] = settings

        class FakeAgent:
            def __init__(
                self,
                model: Any,
                *,
                instructions: str,
                output_type: list[type[Any]],
            ) -> None:
                captured["agent_model"] = model
                captured["instructions"] = instructions
                captured["output_type"] = output_type

            def run_sync(
                self,
                prompt: str,
                *,
                message_history: Sequence[Any] | None = None,
            ) -> FakeRunResult:
                del message_history
                return FakeRunResult(prompt, ())

        previous_banner = pydantic_ai.BANNER_ENABLED
        try:
            with (
                patch("ada.adapters.local_ollama.OllamaProvider", FakeProvider),
                patch("ada.adapters.local_ollama.OllamaModel", FakeModel),
                patch("ada.adapters.local_ollama.Agent", FakeAgent),
            ):
                runtime = build_local_ollama_runtime(LocalOllamaConfig())
        finally:
            pydantic_ai.BANNER_ENABLED = previous_banner

        self.assertIsInstance(runtime, PydanticAIRuntime)
        self.assertEqual(
            captured["output_type"],
            [str, CreateCalendarEventProposal],
        )
        self.assertIn("do not claim it happened", captured["instructions"])

    def test_local_ollama_profile_rejects_non_loopback_endpoints(self) -> None:
        for url in (
            "http://example.com:11434/v1",
            "https://ollama.com/v1",
            "http://192.168.1.10:11434/v1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(LocalModelConfigurationError):
                    validate_local_ollama_base_url(url)

    def test_local_ollama_profile_accepts_loopback_endpoints(self) -> None:
        for url in (
            "http://localhost:11434/v1",
            "http://127.0.0.1:11434/v1/",
            "http://[::1]:11434/v1",
        ):
            with self.subTest(url=url):
                validate_local_ollama_base_url(url)

    def test_local_ollama_profile_requires_v1_endpoint(self) -> None:
        with self.assertRaises(LocalModelConfigurationError):
            validate_local_ollama_base_url("http://localhost:11434/api")


if __name__ == "__main__":
    unittest.main()
