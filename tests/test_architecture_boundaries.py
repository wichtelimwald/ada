from __future__ import annotations

import importlib
import sys
import unittest


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_and_ports_do_not_import_frameworks(self) -> None:
        target_modules = (
            "ada.core.actions",
            "ada.core.authorization",
            "ada.core.action_outcomes",
            "ada.ports.agent_runtime",
            "ada.ports.calendar",
            "ada.ports.travel_time",
            "ada.ports.audit",
            "ada.ports.guard",
            "ada.ports.durable_action",
        )
        framework_modules = ("pydantic_ai", "cedarpy", "dbos")

        # unittest discovery may have imported these modules through other
        # tests already. Clear the targets so this test actually executes
        # their import statements instead of observing cached modules.
        for module_name in (*target_modules, *framework_modules):
            sys.modules.pop(module_name, None)

        for module_name in target_modules:
            importlib.import_module(module_name)

        for module_name in framework_modules:
            self.assertNotIn(module_name, sys.modules)

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
