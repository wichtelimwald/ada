from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from threading import Thread
import unittest
from typing import Any, Sequence
from unittest.mock import patch

import pydantic_ai
import httpx2
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ada.adapters.local_ollama import (
    LocalModelConfigurationError,
    LocalOllamaConfig,
    build_local_ollama_runtime,
    check_local_ollama_ready,
    validate_local_ollama_base_url,
)
from ada.adapters.pydantic_ai import PydanticAIRuntime
from ada.core.actions import CreateCalendarEventDraft
from ada.ports.agent_runtime import AgentRequest, AgentTextReply


class FakeRunResult:
    def __init__(self, output: Any, messages: Sequence[Any]) -> None:
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

    def test_pydantic_runtime_maps_structured_chat_reply_to_text(self) -> None:
        reply = AgentTextReply(text="Hallo aus Ada.")

        class ReplyAgent:
            def run_sync(
                self,
                prompt: str,
                *,
                message_history: Sequence[Any] | None = None,
            ) -> FakeRunResult:
                del prompt, message_history
                return FakeRunResult(reply, ())

        response = PydanticAIRuntime(ReplyAgent()).run(
            AgentRequest(text="hello")
        )

        self.assertEqual(response.text, "Hallo aus Ada.")
        self.assertEqual(response.drafts, ())
        self.assertEqual(response.proposals, ())

    def test_pydantic_runtime_keeps_calendar_draft_out_of_proposals(self) -> None:
        draft = CreateCalendarEventDraft(
            title="Zahnarzt",
            date="21.09.",
            start_time="16:00",
            end_time=None,
            calendar_id="family",
            location=None,
            language="de",
            unresolved=("year", "end_time"),
        )

        class DraftAgent:
            def run_sync(
                self,
                prompt: str,
                *,
                message_history: Sequence[Any] | None = None,
            ) -> FakeRunResult:
                del prompt, message_history
                return FakeRunResult(draft, ())

        response = PydanticAIRuntime(DraftAgent()).run(
            AgentRequest(text="calendar request")
        )

        self.assertEqual(response.drafts, (draft,))
        self.assertEqual(response.proposals, ())
        self.assertEqual(response.text, "")

    def test_real_agent_native_output_and_reset_round_trip(self) -> None:
        captured_histories: list[list[ModelMessage]] = []

        def respond(
            messages: list[ModelMessage],
            info: AgentInfo,
        ) -> ModelResponse:
            captured_histories.append(list(messages))
            self.assertIsNotNone(
                info.model_request_parameters.output_object
            )
            return ModelResponse(
                parts=[
                    TextPart(
                        content=json.dumps(
                            {
                                "result": {
                                    "kind": "AgentTextReply",
                                    "data": {
                                        "text": "Hallo aus dem echten Agent-Pfad.",
                                        "response_type": "chat.reply",
                                    },
                                }
                            }
                        )
                    )
                ]
            )

        previous_banner = pydantic_ai.BANNER_ENABLED
        try:
            pydantic_ai.BANNER_ENABLED = False
            agent = Agent(
                FunctionModel(function=respond),
                output_type=NativeOutput(
                    [AgentTextReply, CreateCalendarEventDraft],
                    name="ada_local_response",
                ),
            )
            runtime = PydanticAIRuntime(
                agent,
                keep_session_history=True,
            )

            first = runtime.run(AgentRequest(text="first"))
            second = runtime.run(AgentRequest(text="second"))
            runtime.reset_session()
            third = runtime.run(AgentRequest(text="after reset"))
        finally:
            pydantic_ai.BANNER_ENABLED = previous_banner

        self.assertEqual(
            first.text,
            "Hallo aus dem echten Agent-Pfad.",
        )
        self.assertEqual(second.text, first.text)
        self.assertEqual(third.text, first.text)
        self.assertEqual(len(captured_histories), 3)
        self.assertGreater(
            len(captured_histories[1]),
            len(captured_histories[0]),
        )
        self.assertEqual(
            len(captured_histories[2]),
            len(captured_histories[0]),
        )

    def test_local_runtime_configures_native_structured_output(self) -> None:
        captured: dict[str, Any] = {}

        class FakeProvider:
            def __init__(self, *, base_url: str, http_client: httpx2.AsyncClient) -> None:
                captured["base_url"] = base_url
                captured["http_client"] = http_client

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
                output_type: Any,
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
        output_type = captured["output_type"]
        self.assertEqual(type(output_type).__name__, "NativeOutput")
        self.assertEqual(output_type.name, "ada_local_response")
        self.assertEqual(
            list(output_type.outputs),
            [AgentTextReply, CreateCalendarEventDraft],
        )
        self.assertIn("Do not invent material details", captured["instructions"])
        self.assertIn("Never claim that a calendar event was created", captured["instructions"])
        asyncio.run(captured["http_client"].aclose())

    def test_local_chat_transport_ignores_proxy_settings(self) -> None:
        hits: list[str] = []

        def make_server(name: str) -> ThreadingHTTPServer:
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    hits.append(name)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"models": [{"name": "qwen3.5:9b"}]}')

                def log_message(self, *args: object) -> None:
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            Thread(target=server.serve_forever, daemon=True).start()
            return server

        proxy, ollama = make_server("proxy"), make_server("ollama")
        url = f"http://localhost:{ollama.server_port}/v1"
        try:
            with patch.dict(os.environ, {
                "http_proxy": f"http://127.0.0.1:{proxy.server_port}",
                "HTTP_PROXY": f"http://127.0.0.1:{proxy.server_port}",
                "ALL_PROXY": f"http://127.0.0.1:{proxy.server_port}",
                "NO_PROXY": "",
                "no_proxy": "",
            }):
                check_local_ollama_ready(LocalOllamaConfig(base_url=url))

                # Inspect the exact client supplied to PydanticAI's provider.
                captured: dict[str, httpx2.AsyncClient] = {}

                class FakeProvider:
                    def __init__(self, *, base_url: str, http_client: httpx2.AsyncClient) -> None:
                        captured["client"] = http_client

                with (
                    patch("ada.adapters.local_ollama.OllamaProvider", FakeProvider),
                    patch("ada.adapters.local_ollama.OllamaModel", lambda *a, **kw: object()),
                    patch("ada.adapters.local_ollama.Agent", lambda *a, **kw: object()),
                ):
                    build_local_ollama_runtime(LocalOllamaConfig(base_url=url))

                async def request() -> None:
                    client = captured["client"]
                    try:
                        response = await client.get(f"http://localhost:{ollama.server_port}/api/tags")
                        self.assertEqual(response.status_code, 200)
                    finally:
                        await client.aclose()

                asyncio.run(request())

            self.assertEqual(hits, ["ollama", "ollama"])
        finally:
            proxy.shutdown()
            ollama.shutdown()

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
