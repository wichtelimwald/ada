from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import textwrap
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


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
                "ada.core.memory_access",
                "ada.ports.agent_runtime",
                "ada.ports.calendar",
                "ada.ports.travel_time",
                "ada.ports.audit",
                "ada.ports.guard",
                "ada.ports.durable_action",
                "ada.ports.personality_memory",
                "ada.ports.memory_broker",
            )
            framework_modules = (
                "pydantic_ai",
                "cedarpy",
                "dbos",
                "httpx2",
                "icalendar",
                "recurring_ical_events",
                "x_wr_timezone",
            )

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

    def test_memory_scope_is_confined_to_the_broker_boundary(self) -> None:
        """Guard PR #46 finding M1: MemoryScope/ProtectionDomainRef must never
        become a de facto authorization capability by being threaded through
        ordinary runtime/storage-adapter code outside the broker boundary."""
        allowed = {
            REPO_ROOT / "src" / "ada" / "core" / "memory_access.py",
            REPO_ROOT / "src" / "ada" / "ports" / "memory_broker.py",
            REPO_ROOT / "src" / "ada" / "adapters" / "in_memory_memory_broker.py",
        }
        token = re.compile(r"\b(MemoryScope|ProtectionDomainRef)\b")

        offenders = []
        for path in (REPO_ROOT / "src" / "ada").rglob("*.py"):
            if path in allowed:
                continue
            if token.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            offenders,
            [],
            "MemoryScope/ProtectionDomainRef must stay inside the broker "
            "boundary (ada.core.memory_access, ada.ports.memory_broker, "
            "ada.adapters.in_memory_memory_broker); found references in: "
            + ", ".join(offenders),
        )

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
