from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    ROUTINE = "routine"
    EPISODE = "episode"


class EvidenceOrigin(StrEnum):
    EXPLICIT_STATEMENT = "explicit_statement"
    OBSERVED_FACT = "observed_fact"
    BEHAVIORAL_OBSERVATION = "behavioral_observation"
    HYPOTHESIS = "hypothesis"


class MemoryLifecycle(StrEnum):
    OBSERVED = "observed"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"
    FORGOTTEN = "forgotten"


class ConfirmationBasis(StrEnum):
    EXPLICIT_USER = "explicit_user"
    OBSERVED_PATTERN = "observed_pattern"


class ForgetResult(StrEnum):
    FORGOTTEN = "forgotten"
    ALREADY_FORGOTTEN = "already_forgotten"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One inspectable Memory or learning item independent from retrieval/runtime."""

    entry_id: str
    kind: MemoryKind
    evidence_origin: EvidenceOrigin
    lifecycle: MemoryLifecycle
    content: str
    confirmation_basis: ConfirmationBasis | None = None
    supports_memory_id: str | None = None


@dataclass(frozen=True, slots=True)
class VersionedMemoryEntry:
    """One current Memory entry plus the revision token read by the caller."""

    entry: MemoryEntry
    revision: str
