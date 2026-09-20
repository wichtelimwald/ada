from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from typing import FrozenSet, Iterable


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class Provenance(str, Enum):
    DIRECT = "direct"
    FORWARDED = "forwarded"
    QUOTED = "quoted"
    MODEL = "model"
    TOOL = "tool"
    WEB = "web"
    FILE = "file"


class Assurance(IntEnum):
    UNVERIFIED = 0
    REGISTERED = 1
    AUTHENTICATED = 2
    LOCAL_TRUSTED = 3


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    actor: str
    action: str
    resource: str
    data_subjects: tuple[str, ...]
    audience: str | None
    purpose: str | None
    provenance: Provenance
    channel: str
    assurance: Assurance
    acting_for: str | None
    now: datetime


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    effect: Effect
    actors: FrozenSet[str] | None = None
    actions: FrozenSet[str] | None = None
    resources: FrozenSet[str] | None = None
    data_subjects: FrozenSet[str] | None = None
    audiences: FrozenSet[str | None] | None = None
    purposes: FrozenSet[str | None] | None = None
    provenances: FrozenSet[Provenance] | None = None
    channels: FrozenSet[str] | None = None
    acting_for: FrozenSet[str | None] | None = None
    min_assurance: Assurance = Assurance.UNVERIFIED
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class GuardDecision:
    effect: Effect
    reason_code: str
    matched_rule_ids: tuple[str, ...]


def _matches(value: object, allowed: FrozenSet[object] | None) -> bool:
    return allowed is None or value in allowed


def _subjects_match(
    request_subjects: tuple[str, ...],
    allowed_subjects: FrozenSet[str] | None,
) -> bool:
    if allowed_subjects is None:
        return True
    return bool(request_subjects) and all(
        subject in allowed_subjects for subject in request_subjects
    )


def _rule_matches(rule: Rule, request: AuthorizationRequest) -> bool:
    if rule.revoked:
        return False
    if rule.valid_from is not None and request.now < rule.valid_from:
        return False
    if rule.valid_until is not None and request.now >= rule.valid_until:
        return False

    return (
        _matches(request.actor, rule.actors)
        and _matches(request.action, rule.actions)
        and _matches(request.resource, rule.resources)
        and _subjects_match(request.data_subjects, rule.data_subjects)
        and _matches(request.audience, rule.audiences)
        and _matches(request.purpose, rule.purposes)
        and _matches(request.provenance, rule.provenances)
        and _matches(request.channel, rule.channels)
        and _matches(request.acting_for, rule.acting_for)
        and request.assurance >= rule.min_assurance
    )


def evaluate(
    request: AuthorizationRequest,
    rules: Iterable[Rule],
    *,
    policy_version: str = "prototype-v1",
) -> GuardDecision:
    del policy_version  # kept in the call shape for the future Ada-owned result type

    if not request.actor or not request.action or not request.resource or not request.channel:
        return GuardDecision(
            effect=Effect.DENY,
            reason_code="invalid_request",
            matched_rule_ids=(),
        )

    matched = [rule for rule in rules if _rule_matches(rule, request)]

    deny_ids = tuple(
        sorted(rule.rule_id for rule in matched if rule.effect is Effect.DENY)
    )
    if deny_ids:
        return GuardDecision(
            effect=Effect.DENY,
            reason_code="explicit_deny",
            matched_rule_ids=deny_ids,
        )

    allow_ids = tuple(
        sorted(rule.rule_id for rule in matched if rule.effect is Effect.ALLOW)
    )
    if allow_ids:
        return GuardDecision(
            effect=Effect.ALLOW,
            reason_code="matching_grant",
            matched_rule_ids=allow_ids,
        )

    return GuardDecision(
        effect=Effect.DENY,
        reason_code="no_matching_grant",
        matched_rule_ids=(),
    )
