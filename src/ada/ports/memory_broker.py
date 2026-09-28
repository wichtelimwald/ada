from __future__ import annotations

from typing import Protocol

from ada.core.memory_access import MemoryAccessContext, MemoryScope


class MemoryBrokerError(RuntimeError):
    """The Memory Broker could not provide a safely scoped capability."""


class MemoryScopeDeniedError(MemoryBrokerError):
    """No exact broker binding authorizes the supplied trusted context."""


class MemoryBrokerPort(Protocol):
    """Broker-internal boundary for exact-match Memory-domain resolution.

    This Protocol is implemented by broker-side code only: the S1 deterministic
    test adapter (``InMemoryMemoryBroker``) and, later, the production broker
    process behind the S2 IPC boundary. Ordinary Ada runtime/storage-adapter code
    must not call ``resolve_scope`` directly and must not accept its return value
    as proof of storage access.
    """

    def resolve_scope(self, context: MemoryAccessContext) -> MemoryScope:
        """Return the exact configured scope or fail closed.

        Implementations must not accept a caller-selected filesystem path, key,
        credential, or additional protection-domain identifier as part of the
        request.

        The returned ``MemoryScope`` is broker-internal, non-authoritative
        metadata, not a bearer capability: it must never be threaded into a later
        storage/provider call as proof of access. A future storage operation must
        re-present the trusted ``MemoryAccessContext`` to this same broker
        boundary rather than reuse a previously resolved scope or domain ID (see
        ADR-0011, "MemoryScope is not an authorization capability").
        """
