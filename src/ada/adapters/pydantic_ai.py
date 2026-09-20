from __future__ import annotations

from typing import Any, Protocol

from ada.core.actions import CreateCalendarEventProposal
from ada.ports.agent_runtime import AgentRequest, AgentResponse, AgentRuntimePort


class _PydanticAgentLike(Protocol):
    """Minimal PydanticAI Agent surface consumed by Ada."""

    def run_sync(self, prompt: str) -> Any:
        """Run one synchronous request."""


class PydanticAIRuntime(AgentRuntimePort):
    """Initial replaceable agent-runtime adapter.

    Model/provider construction is intentionally outside this adapter for now.
    The adapter translates framework results into Ada-owned types and performs
    no privileged side effects.
    """

    def __init__(self, agent: _PydanticAgentLike) -> None:
        self._agent = agent

    def run(self, request: AgentRequest) -> AgentResponse:
        result = self._agent.run_sync(request.text)
        output = result.output

        if isinstance(output, CreateCalendarEventProposal):
            return AgentResponse(text="", proposals=(output,))

        return AgentResponse(text=str(output))
