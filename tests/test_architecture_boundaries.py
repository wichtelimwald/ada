from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_and_ports_do_not_import_frameworks(self) -> None:
        # Run the import check in an isolated interpreter. Mutating sys.modules
        # in this test process would invalidate class identities already held
        # by other discovered test modules and can break DBOS/pickle later in
        # the same suite.
        check = textwrap.dedent(
            """
            import importlib
            import sys

            target_modules = (
                "ada.core.actions",
                "ada.core.authorization",
                "ada.core.action_outcomes",
                "ada.core.personality",
                "ada.core.memory",
                "ada.ports.agent_runtime",
                "ada.ports.calendar",
                "ada.ports.travel_time",
                "ada.ports.audit",
                "ada.ports.guard",
                "ada.ports.durable_action",
                "ada.ports.personality_memory",
            )
            framework_modules = ("pydantic_ai", "cedarpy", "dbos")

            for module_name in target_modules:
                importlib.import_module(module_name)

            imported_frameworks = [
                module_name
                for module_name in framework_modules
                if module_name in sys.modules
            ]
            if imported_frameworks:
                raise SystemExit(
                    "Ada core/ports imported forbidden frameworks: "
                    + ", ".join(imported_frameworks)
                )
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", check],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

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
