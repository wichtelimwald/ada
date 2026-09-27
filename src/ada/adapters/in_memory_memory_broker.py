from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ada.core.memory_access import (
    MemoryAccessContext,
    MemoryScope,
    ProtectionDomainKind,
    ProtectionDomainRef,
)
from ada.ports.memory_broker import (
    MemoryBrokerError,
    MemoryScopeDeniedError,
)


class MemoryBrokerConfigurationError(MemoryBrokerError):
    """The broker's trusted scope configuration is ambiguous or inconsistent."""


@dataclass(frozen=True, slots=True)
class MemoryScopeBinding:
    context: MemoryAccessContext
    domains: tuple[ProtectionDomainRef, ...]


class InMemoryMemoryBroker:
    """Deterministic broker contract adapter for tests/development only.

    This adapter intentionally holds all configured bindings in one process. It is
    not an enforceable production protection boundary and must not be used with
    real household Memory. The production MVP-30 adapter remains a separate
    host-side process.
    """

    def __init__(self, bindings: Iterable[MemoryScopeBinding]) -> None:
        self._bindings: dict[MemoryAccessContext, MemoryScope] = {}
        domain_kinds: dict[str, ProtectionDomainKind] = {}

        for binding in bindings:
            if binding.context in self._bindings:
                raise MemoryBrokerConfigurationError(
                    "duplicate Memory broker context binding"
                )

            scope = MemoryScope(binding.domains)
            for domain in scope.domains:
                existing_kind = domain_kinds.get(domain.domain_id)
                if existing_kind is not None and existing_kind is not domain.kind:
                    raise MemoryBrokerConfigurationError(
                        "one protection-domain ID is configured with multiple kinds"
                    )
                domain_kinds[domain.domain_id] = domain.kind

            self._bindings[binding.context] = scope

    def resolve_scope(self, context: MemoryAccessContext) -> MemoryScope:
        try:
            return self._bindings[context]
        except KeyError as exc:
            raise MemoryScopeDeniedError(
                "Memory access context has no exact broker scope binding"
            ) from exc
