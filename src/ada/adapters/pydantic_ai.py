from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from ada.ports.agent_runtime import AgentRequest, AgentResponse, AgentRuntimePort

if TYPE_CHECKING:
    from pydantic_ai import Agent


class _PydanticAgentLike(Protocol):
    def run_sync(self, prompt: str) -> Any:
        """Subset of PydanticAI Agent used by this adapter."""


class PydanticAIRuntime(AgentRuntimePort):
    """Initial runtime adapter.

    Model/provider construction is intentionally outside this adapter for now.
    The adapter translates framework results into Ada-owned types and performs
    no privileged side effects.
    """

    def __init__(self, agent: _PydanticAgentLike | "Agent[Any, Any]") -> None:
        self._agent = agent

    def run(self, request: AgentRequest) -> AgentResponse:
        result = self._agent.run_sync(request.text)
        return AgentResponse(text=str(result.output))
