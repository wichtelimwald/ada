from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from cedarpy import Decision, PolicySet, Schema, is_authorized, validate_policies


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


class Assurance(str, Enum):
    UNVERIFIED = "unverified"
    REGISTERED = "registered"
    AUTHENTICATED = "authenticated"
    LOCAL_TRUSTED = "local_trusted"


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    actor: str
    action: str
    resource: str
    data_subjects: tuple[str, ...] = ()
    audience: str | None = None
    purpose: str | None = None
    provenance: Provenance = Provenance.DIRECT
    channel: str = "local-chat"
    assurance: Assurance = Assurance.UNVERIFIED
    acting_for: str | None = None
    now_epoch_ms: int = 0


@dataclass(frozen=True, slots=True)
class GuardDecision:
    effect: Effect
    reason_code: str
    matched_rule_ids: tuple[str, ...]
    policy_version: str


SCHEMA = """
entity Actor;
entity AdaResource;

type RequestContext = {
    provenance: String,
    channel: String,
    assurance: String,
    purpose?: String,
    audience?: String,
    actingFor?: String,
    nowEpochMs: Long
};

action "calendar.create",
       "approval.simple",
       "calendar.disclose.busy",
       "calendar.disclose.detail"
appliesTo {
    principal: Actor,
    resource: AdaResource,
    context: RequestContext
};
"""


class CedarGuard:
    """Thin Ada-owned bridge around the Cedar authorizer."""

    def __init__(
        self,
        policies: str,
        *,
        policy_version: str = "prototype-v1",
        schema_text: str = SCHEMA,
    ) -> None:
        self._policy_version = policy_version
        self._schema = Schema.from_str(schema_text)
        self._policies = PolicySet.from_str(policies)

        validation = validate_policies(self._policies, self._schema)
        if not validation.validation_passed:
            errors = "; ".join(str(error) for error in validation.errors)
            raise ValueError(f"invalid Cedar policy set: {errors}")

    def authorize(self, request: AuthorizationRequest) -> GuardDecision:
        if not request.actor or not request.action or not request.resource or not request.channel:
            return self._deny("invalid_request")

        context: dict[str, object] = {
            "provenance": request.provenance.value,
            "channel": request.channel,
            "assurance": request.assurance.value,
            "nowEpochMs": request.now_epoch_ms,
        }
        if request.purpose is not None:
            context["purpose"] = request.purpose
        if request.audience is not None:
            context["audience"] = request.audience
        if request.acting_for is not None:
            context["actingFor"] = request.acting_for

        cedar_request = {
            "principal": {"type": "Actor", "id": request.actor},
            "action": {"type": "Action", "id": request.action},
            "resource": {"type": "AdaResource", "id": request.resource},
            "context": context,
        }

        try:
            result = is_authorized(
                cedar_request,
                self._policies,
                [],
                schema=self._schema,
            )
        except Exception:
            return self._deny("cedar_error")

        # Cedar intentionally records individual policy evaluation errors in
        # diagnostics and can still return Allow from another matching permit.
        # Ada's root boundary is stricter: any evaluation error fails closed.
        if result.diagnostics.errors:
            return self._deny("cedar_evaluation_error")

        if result.decision == Decision.Allow:
            return GuardDecision(
                effect=Effect.ALLOW,
                reason_code="matching_grant",
                matched_rule_ids=tuple(sorted(result.diagnostics.reasons)),
                policy_version=self._policy_version,
            )

        if result.decision == Decision.Deny:
            reason = (
                "explicit_deny"
                if result.diagnostics.reasons
                else "no_matching_grant"
            )
            return GuardDecision(
                effect=Effect.DENY,
                reason_code=reason,
                matched_rule_ids=tuple(sorted(result.diagnostics.reasons)),
                policy_version=self._policy_version,
            )

        return self._deny("cedar_no_decision")

    def _deny(self, reason_code: str) -> GuardDecision:
        return GuardDecision(
            effect=Effect.DENY,
            reason_code=reason_code,
            matched_rule_ids=(),
            policy_version=self._policy_version,
        )
