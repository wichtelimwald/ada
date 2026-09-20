from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from cedarpy import Decision, PolicySet, Schema, is_authorized, validate_policies

from ada.core.authorization import (
    AuthorizationRequest,
    GuardDecision,
    GuardEffect,
)
from ada.ports.guard import AdaGuard


DEFAULT_SCHEMA = """
entity Actor;
entity AdaResource;

type RequestContext = {
    dataSubjects: Set<String>,
    provenance: String,
    channel: String,
    assurance: String,
    purpose?: String,
    audience?: String,
    actingFor?: String,
    nowEpochMs: Long
};

action "calendar.create" appliesTo {
    principal: Actor,
    resource: AdaResource,
    context: RequestContext
};

action "approval.simple" appliesTo {
    principal: Actor,
    resource: AdaResource,
    context: RequestContext
};

action "calendar.disclose.busy" appliesTo {
    principal: Actor,
    resource: AdaResource,
    context: RequestContext
};

action "calendar.disclose.detail" appliesTo {
    principal: Actor,
    resource: AdaResource,
    context: RequestContext
};
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CedarGuard(AdaGuard):
    """Thin Ada-owned fail-closed adapter around Cedar."""

    def __init__(
        self,
        policies: str,
        *,
        policy_version: str,
        schema_text: str = DEFAULT_SCHEMA,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._policy_version = policy_version
        self._clock = clock

        self._schema = Schema.from_str(schema_text)

        validation = validate_policies(policies, self._schema)
        if not validation.validation_passed:
            errors = "; ".join(str(error) for error in validation.errors)
            raise ValueError(f"invalid Cedar policy set: {errors}")

        self._policies = PolicySet.from_str(policies)

    def authorize(self, request: AuthorizationRequest) -> GuardDecision:
        if (
            not request.actor
            or not request.action
            or not request.resource
            or not request.channel
        ):
            return self._deny("invalid_request")

        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            return self._deny("invalid_guard_clock")

        context: dict[str, object] = {
            "dataSubjects": list(request.data_subjects),
            "provenance": request.provenance.value,
            "channel": request.channel,
            "assurance": request.assurance.value,
            "nowEpochMs": int(now.timestamp() * 1000),
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

        if result.diagnostics.errors:
            return self._deny("cedar_evaluation_error")

        matched_rule_ids = tuple(
            sorted(
                result.diagnostics.id_annotations_by_reason.get(
                    policy_id,
                    policy_id,
                )
                for policy_id in result.diagnostics.reasons
            )
        )

        if result.decision == Decision.Allow:
            return GuardDecision(
                effect=GuardEffect.ALLOW,
                reason_code="matching_grant",
                matched_rule_ids=matched_rule_ids,
                policy_version=self._policy_version,
            )

        if result.decision == Decision.Deny:
            reason_code = (
                "explicit_deny"
                if result.diagnostics.reasons
                else "no_matching_grant"
            )
            return GuardDecision(
                effect=GuardEffect.DENY,
                reason_code=reason_code,
                matched_rule_ids=matched_rule_ids,
                policy_version=self._policy_version,
            )

        return self._deny("cedar_no_decision")

    def _deny(self, reason_code: str) -> GuardDecision:
        return GuardDecision(
            effect=GuardEffect.DENY,
            reason_code=reason_code,
            matched_rule_ids=(),
            policy_version=self._policy_version,
        )
