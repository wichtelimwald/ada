from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GuardEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class InstructionProvenance(str, Enum):
    DIRECT = "direct"
    FORWARDED = "forwarded"
    QUOTED = "quoted"
    MODEL = "model"
    TOOL = "tool"
    WEB = "web"
    FILE = "file"


class AuthenticationAssurance(str, Enum):
    UNVERIFIED = "unverified"
    REGISTERED = "registered"
    AUTHENTICATED = "authenticated"
    LOCAL_TRUSTED = "local_trusted"


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """Ada-owned authorization input.

    Identity, assurance, and provenance are established outside the policy
    engine. Model output must never upgrade these claims.
    """

    actor: str
    action: str
    resource: str
    provenance: InstructionProvenance
    channel: str
    data_subjects: tuple[str, ...] = ()
    audience: str | None = None
    purpose: str | None = None
    assurance: AuthenticationAssurance = AuthenticationAssurance.UNVERIFIED
    acting_for: str | None = None


@dataclass(frozen=True, slots=True)
class GuardDecision:
    """Framework-neutral authorization result owned by Ada."""

    effect: GuardEffect
    reason_code: str
    matched_rule_ids: tuple[str, ...]
    policy_version: str

    @property
    def allowed(self) -> bool:
        return self.effect is GuardEffect.ALLOW
