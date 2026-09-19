from __future__ import annotations

import importlib
import sys
import unittest


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_and_ports_do_not_import_pydantic_ai(self) -> None:
        sys.modules.pop("pydantic_ai", None)

        importlib.import_module("ada.core.actions")
        importlib.import_module("ada.ports.agent_runtime")
        importlib.import_module("ada.ports.calendar")
        importlib.import_module("ada.ports.travel_time")
        importlib.import_module("ada.ports.audit")

        self.assertNotIn("pydantic_ai", sys.modules)

    def test_pydantic_adapter_returns_ada_owned_result(self) -> None:
        from ada.adapters.pydantic_ai import PydanticAIRuntime
        from ada.ports.agent_runtime import AgentRequest, AgentResponse

        class FakeResult:
            output = "hello from fake runtime"

        class FakeAgent:
            def run_sync(self, prompt: str) -> FakeResult:
                self.prompt = prompt
                return FakeResult()

        fake = FakeAgent()
        runtime = PydanticAIRuntime(fake)

        response = runtime.run(AgentRequest(text="hello"))

        self.assertIsInstance(response, AgentResponse)
        self.assertEqual(response.text, "hello from fake runtime")
        self.assertEqual(response.proposals, ())
        self.assertEqual(fake.prompt, "hello")


if __name__ == "__main__":
    unittest.main()
