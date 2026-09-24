from __future__ import annotations

import asyncio
from io import StringIO
import json
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch

from ada.cli import _chat, _chat_loop, build_parser
from ada.core.actions import CreateCalendarEventDraft
from ada.ports.agent_runtime import AgentRequest, AgentResponse


class FakeChatRuntime:
    def __init__(self) -> None:
        self.requests: list[str] = []
        self.reset_count = 0

    def run(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request.text)
        return AgentResponse(text=f"echo:{request.text}")

    def reset_session(self) -> None:
        self.reset_count += 1


class DraftRuntime:
    def run(self, request: AgentRequest) -> AgentResponse:
        del request
        return AgentResponse(
            text="",
            drafts=(
                CreateCalendarEventDraft(
                    title="Zahnarzt",
                    date="21.09.",
                    start_time="16:00",
                    end_time=None,
                    calendar_id="family",
                    location=None,
                    language="de",
                    unresolved=("year", "end_time"),
                ),
            ),
        )


class TextRuntime:
    def __init__(self, text: str) -> None:
        self.text = text

    def run(self, request: AgentRequest) -> AgentResponse:
        del request
        return AgentResponse(text=self.text)


class FalseCompletionRuntime:
    def run(self, request: AgentRequest) -> AgentResponse:
        del request
        return AgentResponse(text="Ich habe den Termin eingetragen.")


class StandaloneDoneRuntime:
    def run(self, request: AgentRequest) -> AgentResponse:
        del request
        return AgentResponse(text="Erledigt.")


class FailingRuntime:
    def run(self, request: AgentRequest) -> AgentResponse:
        del request
        raise RuntimeError("synthetic model parse failure")


class CliTests(unittest.TestCase):
    def test_chat_closes_runtime_on_quit_interrupt_and_failure(self) -> None:
        for outcome, expected in (
            (0, 0),
            (KeyboardInterrupt(), 130),
            (RuntimeError("boom"), 1),
        ):
            with self.subTest(outcome=outcome):
                runtime = FakeChatRuntime()
                runtime.aclose = AsyncMock()
                with (
                    patch("ada.adapters.local_ollama.check_local_ollama_ready"),
                    patch(
                        "ada.adapters.local_ollama.build_local_ollama_runtime",
                        return_value=runtime,
                    ),
                    patch(
                        "ada.cli._chat_loop",
                        side_effect=outcome if isinstance(outcome, BaseException) else None,
                        return_value=outcome if isinstance(outcome, int) else None,
                    ),
                ):
                    self.assertEqual(
                        _chat(model="qwen3.5:9b", ollama_url="http://localhost:11434/v1"),
                        expected,
                    )
                runtime.aclose.assert_awaited_once_with()

    def test_chat_closes_on_request_loop_without_masking_exit_code(self) -> None:
        class LoopRuntime(FakeChatRuntime):
            request_loop: asyncio.AbstractEventLoop | None = None
            close_loop: asyncio.AbstractEventLoop | None = None

            def run(self, request: AgentRequest) -> AgentResponse:
                self.request_loop = asyncio.get_event_loop()
                return super().run(request)

            async def aclose(self) -> None:
                self.close_loop = asyncio.get_running_loop()
                raise RuntimeError("synthetic cleanup failure")

        runtime = LoopRuntime()
        inputs = iter(("hello", "/quit"))
        stderr = StringIO()
        with (
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch(
                "ada.adapters.local_ollama.build_local_ollama_runtime",
                return_value=runtime,
            ),
            patch(
                "ada.cli._chat_loop",
                side_effect=lambda active: _chat_loop(
                    active, read=lambda prompt: next(inputs), write=lambda message: None
                ),
            ),
            patch("ada.cli.sys.stderr", stderr),
        ):
            result = _chat(model="qwen3.5:9b", ollama_url="http://localhost:11434/v1")

        self.assertEqual(result, 0)
        self.assertIs(runtime.request_loop, runtime.close_loop)
        self.assertIn("warning: local model cleanup failed", stderr.getvalue())

        interrupt_runtime = LoopRuntime()
        with (
            patch("ada.adapters.local_ollama.check_local_ollama_ready"),
            patch(
                "ada.adapters.local_ollama.build_local_ollama_runtime",
                return_value=interrupt_runtime,
            ),
            patch("ada.cli._chat_loop", side_effect=KeyboardInterrupt),
            patch("ada.cli.sys.stderr", StringIO()),
        ):
            self.assertEqual(
                _chat(model="qwen3.5:9b", ollama_url="http://localhost:11434/v1"),
                130,
            )
        self.assertIsNotNone(interrupt_runtime.close_loop)

    def test_chat_defaults_to_qwen35_9b(self) -> None:
        with patch("ada.cli.os.getenv", side_effect=lambda key, default=None: default):
            args = build_parser().parse_args(["chat"])

        self.assertEqual(args.model, "qwen3.5:9b")

    def test_doctor(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ada", "doctor"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("python", payload)

    def test_chat_renders_calendar_draft_without_execution_claim(self) -> None:
        inputs = iter(("add dentist appointment", "/quit"))
        output: list[str] = []

        result = _chat_loop(
            DraftRuntime(),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        joined = "\n".join(output)
        self.assertIn("noch nichts in den Kalender eingetragen", joined)
        self.assertIn("Endzeit oder Dauer", joined)
        self.assertNotIn("Termin wurde eingetragen", joined)
        self.assertNotIn("appointment was created", joined)

    def test_chat_marks_false_completion_as_conversation_only(self) -> None:
        inputs = iter((
            "Kannst du den Termin in den Kalender eintragen?",
            "/quit",
        ))
        output: list[str] = []

        result = _chat_loop(
            FalseCompletionRuntime(),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        joined = "\n".join(output)
        self.assertIn("Ich habe den Termin eingetragen.", joined)
        self.assertIn(
            "Conversation only: no external action was executed in this turn.",
            joined,
        )

    def test_chat_sanitizes_terminal_controls_before_status_marker(self) -> None:
        reply = "Looks fine.\x1b[8mHIDDEN"
        inputs = iter(("hello", "/quit"))
        output: list[str] = []

        result = _chat_loop(
            TextRuntime(reply),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        joined = "\n".join(output)
        self.assertNotIn("\x1b", joined)
        self.assertIn("Looks fine.[8mHIDDEN", joined)
        self.assertIn(
            "Conversation only: no external action was executed in this turn.",
            joined,
        )

    def test_chat_marks_standalone_erledigt_as_conversation_only(self) -> None:
        inputs = iter((
            "Zahnarzttermin morgen um 16 Uhr",
            "/quit",
        ))
        output: list[str] = []

        result = _chat_loop(
            StandaloneDoneRuntime(),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        joined = "\n".join(output)
        self.assertIn("Erledigt.", joined)
        self.assertIn(
            "Conversation only: no external action was executed in this turn.",
            joined,
        )

    def test_chat_marks_all_free_text_as_non_authoritative(self) -> None:
        replies = (
            "I added the appointment.",
            "Added to your calendar.",
            "Your calendar has been updated.",
            "Which calendar should I use?",
            "A calendar is a way to organize dates and events.",
        )

        for reply in replies:
            with self.subTest(reply=reply):
                inputs = iter(("ordinary free text turn", "/quit"))
                output: list[str] = []

                result = _chat_loop(
                    TextRuntime(reply),
                    read=lambda prompt: next(inputs),
                    write=output.append,
                )

                self.assertEqual(result, 0)
                joined = "\n".join(output)
                self.assertIn(reply, joined)
                self.assertIn(
                    "Conversation only: no external action was executed in this turn.",
                    joined,
                )

    def test_chat_recovers_from_runtime_error_without_action_claim(self) -> None:
        inputs = iter(("calendar request", "/quit"))
        output: list[str] = []

        result = _chat_loop(
            FailingRuntime(),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        self.assertIn(
            "Ada: I could not reliably process that request. No action was executed.",
            output,
        )

    def test_chat_loop_keeps_running_and_can_reset_session(self) -> None:
        runtime = FakeChatRuntime()
        inputs = iter(("hello", "/reset", "again", "/quit"))
        prompts: list[str] = []
        output: list[str] = []

        def read(prompt: str) -> str:
            prompts.append(prompt)
            return next(inputs)

        result = _chat_loop(
            runtime,
            read=read,
            write=output.append,
        )

        self.assertEqual(result, 0)
        self.assertEqual(runtime.requests, ["hello", "again"])
        self.assertEqual(runtime.reset_count, 1)
        self.assertEqual(prompts, ["you> "] * 4)
        self.assertTrue(
            any(
                item.startswith("Ada: echo:hello\n")
                and "Conversation only: no external action was executed in this turn."
                in item
                for item in output
            )
        )
        self.assertIn("Ada: Session context cleared.", output)


if __name__ == "__main__":
    unittest.main()
