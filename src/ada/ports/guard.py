from __future__ import annotations

from typing import Protocol

from ada.core.authorization import AuthorizationRequest, GuardDecision


class AdaGuard(Protocol):
    """Stable Ada authorization boundary."""

    def authorize(self, request: AuthorizationRequest) -> GuardDecision:
        """Evaluate one request without performing the privileged action."""
