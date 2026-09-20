from __future__ import annotations

import json
import subprocess
import sys
import unittest

from ada.cli import _chat_loop
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


class CliTests(unittest.TestCase):
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
