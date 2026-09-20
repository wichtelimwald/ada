from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OperationId(str):
    """Stable Ada identity for one consequential operation."""

    def __new__(cls, value: str) -> "OperationId":
        normalized = value.strip()
        if not normalized:
            raise ValueError("operation_id must not be empty")
        return str.__new__(cls, normalized)


class ProviderCapability(str, Enum):
    """Duplicate-safety capability exposed by a provider adapter."""

    IDEMPOTENT = "idempotent"
    RECONCILABLE = "reconcilable"
    NONE = "none"


class ProviderOutcomeStatus(str, Enum):
    COMMITTED = "committed"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ProviderOutcome:
    """What Ada can prove about the external provider effect."""

    status: ProviderOutcomeStatus
    provider_reference: str | None = None
    error_code: str | None = None


class BusinessOutcomeStatus(str, Enum):
    COMMITTED = "committed"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class BusinessOutcome:
    """Ada's user-facing interpretation, bounded by provider evidence."""

    status: BusinessOutcomeStatus
    summary_code: str


@dataclass(frozen=True, slots=True)
class AuthorizationEvidence:
    """Minimal Guard evidence persisted with a durable action."""

    policy_version: str
    matched_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActionExecutionResult:
    operation_id: OperationId
    provider: ProviderOutcome
    business: BusinessOutcome


def business_outcome_from_provider(outcome: ProviderOutcome) -> BusinessOutcome:
    """Never claim a stronger business outcome than provider evidence supports."""

    if outcome.status is ProviderOutcomeStatus.COMMITTED:
        return BusinessOutcome(
            status=BusinessOutcomeStatus.COMMITTED,
            summary_code="provider_commit_confirmed",
        )
    if outcome.status is ProviderOutcomeStatus.FAILED:
        return BusinessOutcome(
            status=BusinessOutcomeStatus.FAILED,
            summary_code="provider_non_commit_confirmed",
        )
    return BusinessOutcome(
        status=BusinessOutcomeStatus.AMBIGUOUS,
        summary_code="provider_outcome_ambiguous",
    )
