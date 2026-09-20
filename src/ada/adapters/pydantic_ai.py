from __future__ import annotations

from typing import Any, Protocol, Sequence

from ada.core.actions import CreateCalendarEventProposal
from ada.ports.agent_runtime import AgentRequest, AgentResponse, AgentRuntimePort


class _PydanticAgentLike(Protocol):
    """Minimal PydanticAI Agent surface consumed by Ada."""

    def run_sync(
        self,
        prompt: str,
        *,
        message_history: Sequence[Any] | None = None,
    ) -> Any:
        """Run one synchronous request."""


class PydanticAIRuntime(AgentRuntimePort):
    """Initial replaceable agent-runtime adapter.

    Model/provider construction is intentionally outside this adapter. The
    adapter translates framework results into Ada-owned types and performs no
    privileged side effects.

    Optional session history is ephemeral runtime state only. It is not Ada's
    authoritative Memory and is discarded with this runtime instance.
    """

    def __init__(
        self,
        agent: _PydanticAgentLike,
        *,
        keep_session_history: bool = False,
    ) -> None:
        self._agent = agent
        self._keep_session_history = keep_session_history
        self._message_history: tuple[Any, ...] = ()

    def run(self, request: AgentRequest) -> AgentResponse:
        if self._keep_session_history and self._message_history:
            result = self._agent.run_sync(
                request.text,
                message_history=self._message_history,
            )
        else:
            result = self._agent.run_sync(request.text)

        if self._keep_session_history:
            all_messages = getattr(result, "all_messages", None)
            if callable(all_messages):
                self._message_history = tuple(all_messages())

        output = result.output
        if isinstance(output, CreateCalendarEventProposal):
            return AgentResponse(text="", proposals=(output,))

        return AgentResponse(text=str(output))

    def reset_session(self) -> None:
        """Forget ephemeral conversation context held by this adapter."""

        self._message_history = ()
