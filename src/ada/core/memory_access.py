from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re


_DOMAIN_ID = re.compile(r"pd-[0-9a-f]{32}\Z")
_CONTEXT_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class ProtectionDomainKind(StrEnum):
    PERSON_PRIVATE = "person_private"
    FAMILY_SHARED = "family_shared"
    ADA_SYSTEM = "ada_system"


class MemoryAccessOperation(StrEnum):
    READ_CURRENT = "read_current"
    WRITE_CURRENT = "write_current"


def _require_context_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or _CONTEXT_TOKEN.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must be a non-empty opaque token using only "
            "letters, digits, '.', '_', ':', or '-'"
        )


@dataclass(frozen=True, slots=True)
class ProtectionDomainRef:
    """Opaque reference to one Memory protection domain.

    Storage paths, encryption keys and provider credentials deliberately do not
    cross this Ada-owned boundary.

    This is broker-internal, non-authoritative metadata, not a bearer
    capability: equality is defined only by the opaque ``domain_id``/``kind``
    fields below, and constructing or possessing an instance grants no storage
    access by itself. Only ``ada.ports.memory_broker`` and its broker-side
    implementations may treat resolution of this type as authoritative; no
    other module may import it (enforced by
    ``tests.test_architecture_boundaries``).
    """

    domain_id: str
    kind: ProtectionDomainKind

    def __post_init__(self) -> None:
        if not isinstance(self.domain_id, str) or _DOMAIN_ID.fullmatch(
            self.domain_id
        ) is None:
            raise ValueError(
                "protection-domain IDs must be opaque pd-<32 lowercase hex> values"
            )
        if not isinstance(self.kind, ProtectionDomainKind):
            raise TypeError("kind must be a ProtectionDomainKind")


@dataclass(frozen=True, slots=True)
class MemoryAccessContext:
    """Trusted Ada application context presented to the Memory Broker.

    The context intentionally contains no caller-selectable protection-domain
    identifier. A broker resolves an exact actor/audience/authorization/operation
    binding to its configured domains and fails closed when no binding exists.

    Constructing this value is not authentication. The production boundary must
    receive these fields only from Ada-owned trusted context, never from model or
    retrieved-content claims.
    """

    actor_ref: str
    audience_ref: str
    authorization_ref: str
    operation: MemoryAccessOperation

    def __post_init__(self) -> None:
        _require_context_token(self.actor_ref, field_name="actor_ref")
        _require_context_token(self.audience_ref, field_name="audience_ref")
        _require_context_token(
            self.authorization_ref,
            field_name="authorization_ref",
        )
        if not isinstance(self.operation, MemoryAccessOperation):
            raise TypeError("operation must be a MemoryAccessOperation")


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """Resolved broker scope with no filesystem, key or credential material.

    This is broker-internal, non-authoritative metadata returned by
    ``MemoryBrokerPort.resolve_scope()`` for deterministic S1 testing. It is not
    an authorization capability: nothing outside the broker boundary may accept
    a ``MemoryScope`` (or the domain IDs inside it) as proof of storage access.
    A future storage operation must re-present the trusted
    ``MemoryAccessContext`` to the broker rather than reuse a previously
    resolved scope. See ADR-0011, "MemoryScope is not an authorization
    capability".
    """

    domains: tuple[ProtectionDomainRef, ...]

    def __post_init__(self) -> None:
        if not self.domains:
            raise ValueError("a resolved Memory scope must contain at least one domain")
        domain_ids = [domain.domain_id for domain in self.domains]
        if len(domain_ids) != len(set(domain_ids)):
            raise ValueError("a resolved Memory scope must not repeat a domain")
        object.__setattr__(
            self,
            "domains",
            tuple(sorted(self.domains, key=lambda domain: domain.domain_id)),
        )
