from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from ada.cli import _chat_loop, build_parser
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

    def test_chat_blocks_unverified_calendar_completion_claim(self) -> None:
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
        self.assertNotIn("Ich habe den Termin eingetragen.", joined)
        self.assertIn("No calendar action was executed.", joined)

    def test_chat_blocks_standalone_done_for_compound_appointment(self) -> None:
        inputs = iter((
            "Trag den Zahnarzttermin ein.",
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
        self.assertNotIn("Ada: Erledigt.", joined)
        self.assertIn("No calendar action was executed.", joined)

    def test_chat_blocks_free_text_for_calendar_action_requests(self) -> None:
        replies = (
            "I added the appointment.",
            "Added to your calendar.",
            "Your calendar has been updated.",
            "Which calendar should I use?",
        )
        request = "Please add the appointment to my calendar."

        for reply in replies:
            with self.subTest(reply=reply):
                inputs = iter((request, "/quit"))
                output: list[str] = []

                result = _chat_loop(
                    TextRuntime(reply),
                    read=lambda prompt: next(inputs),
                    write=output.append,
                )

                self.assertEqual(result, 0)
                joined = "\n".join(output)
                self.assertNotIn(reply, joined)
                self.assertIn("No calendar action was executed.", joined)

    def test_chat_keeps_free_text_for_non_action_calendar_discussion(self) -> None:
        reply = "A calendar is a way to organize dates and events."
        inputs = iter(("What is a calendar?", "/quit"))
        output: list[str] = []

        result = _chat_loop(
            TextRuntime(reply),
            read=lambda prompt: next(inputs),
            write=output.append,
        )

        self.assertEqual(result, 0)
        self.assertIn(f"Ada: {reply}", output)

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
        self.assertIn("Ada: echo:hello", output)
        self.assertIn("Ada: Session context cleared.", output)


if __name__ == "__main__":
    unittest.main()
