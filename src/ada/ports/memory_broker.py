from __future__ import annotations

from typing import Protocol

from ada.core.memory_access import MemoryAccessContext, MemoryScope


class MemoryBrokerError(RuntimeError):
    """The Memory Broker could not provide a safely scoped capability."""


class MemoryScopeDeniedError(MemoryBrokerError):
    """No exact broker binding authorizes the supplied trusted context."""


class MemoryBrokerPort(Protocol):
    """Ada-owned boundary for request-scoped Memory-domain resolution."""

    def resolve_scope(self, context: MemoryAccessContext) -> MemoryScope:
        """Return the exact configured scope or fail closed.

        Implementations must not accept a caller-selected filesystem path, key,
        credential, or additional protection-domain identifier as part of the
        request.
        """
