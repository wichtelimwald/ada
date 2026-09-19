from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ada.core.actions import ActionProposal


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """Framework-neutral request passed into an agent runtime adapter."""

    text: str


@dataclass(frozen=True, slots=True)
class AgentResponse:
    """Framework-neutral result returned by an agent runtime adapter."""

    text: str
    proposals: tuple[ActionProposal, ...] = ()


class AgentRuntimePort(Protocol):
    """Replaceable model/agent runtime boundary owned by Ada."""

    def run(self, request: AgentRequest) -> AgentResponse:
        """Handle one request without making privileged provider writes."""
