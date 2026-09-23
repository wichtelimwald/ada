from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from ada.adapters.cedar_guard import CedarGuard
from ada.core.authorization import (
    AuthenticationAssurance,
    AuthorizationRequest,
    GuardEffect,
    InstructionProvenance,
)


NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return NOW


def request(**changes: object) -> AuthorizationRequest:
    values: dict[str, object] = {
        "actor": "guardian-a",
        "action": "calendar.create",
        "resource": "calendar:family",
        "data_subjects": ("child-a",),
        "audience": "family",
        "purpose": "family-coordination",
        "provenance": InstructionProvenance.DIRECT,
        "channel": "local-chat",
        "assurance": AuthenticationAssurance.LOCAL_TRUSTED,
        "acting_for": None,
    }
    values.update(changes)
    return AuthorizationRequest(**values)


class RequiredContextTests(unittest.TestCase):
    def test_provenance_must_be_supplied(self) -> None:
        with self.assertRaises(TypeError):
            AuthorizationRequest(  # type: ignore[call-arg]
                actor="guardian-a", action="calendar.create",
                resource="calendar:family", channel="local-chat",
            )

    def test_channel_must_be_supplied(self) -> None:
        with self.assertRaises(TypeError):
            AuthorizationRequest(  # type: ignore[call-arg]
                actor="guardian-a", action="calendar.create",
                resource="calendar:family", provenance=InstructionProvenance.DIRECT,
            )


CALENDAR_GRANT = """
@id("grant-school-calendar")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.create",
    resource == AdaResource::"calendar:family"
)
when {
    context.provenance == "direct" &&
    (context.assurance == "authenticated" ||
     context.assurance == "local_trusted")
};
"""

DENY_OVERRIDE = CALENDAR_GRANT + """
@id("deny-private-calendar-create")
forbid (
    principal == Actor::"guardian-a",
    action == Action::"calendar.create",
    resource == AdaResource::"calendar:family"
)
when {
    context has purpose &&
    context.purpose == "private-medical"
};
"""

EMAIL_APPROVAL = """
@id("one-off-email-approval")
permit (
    principal == Actor::"guardian-a",
    action == Action::"approval.simple",
    resource == AdaResource::"operation:calendar:123"
)
when {
    context.provenance == "direct" &&
    context.channel == "email" &&
    context.assurance == "authenticated"
};
"""

LOCAL_APPROVAL = """
@id("one-off-local-approval")
permit (
    principal == Actor::"guardian-a",
    action == Action::"approval.simple",
    resource == AdaResource::"operation:calendar:123"
)
when {
    context.provenance == "direct" &&
    context.channel == "local-chat" &&
    context.assurance == "local_trusted"
};
"""

EXPIRED_GRANT = """
@id("expired-calendar-grant")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.create",
    resource == AdaResource::"calendar:family"
)
when {
    context.nowEpochMs < 1700000000000
};
"""

DISCLOSURE_POLICIES = """
@id("allow-family-busy-view")
permit (
    principal,
    action == Action::"calendar.disclose.busy",
    resource == AdaResource::"event:parent-a-private"
)
when {
    context has audience &&
    context.audience == "family"
};

@id("allow-family-calendar-read")
permit (
    principal,
    action == Action::"calendar.disclose.detail",
    resource == AdaResource::"event:parent-a-private"
)
when {
    context has audience &&
    context.audience == "family"
};

@id("deny-private-detail-to-family")
forbid (
    principal,
    action == Action::"calendar.disclose.detail",
    resource == AdaResource::"event:parent-a-private"
)
when {
    context has audience &&
    context.audience == "family"
};
"""

SUBJECT_SCOPED_POLICY = """
@id("child-a-calendar")
permit (
    principal == Actor::"guardian-a",
    action == Action::"calendar.create",
    resource == AdaResource::"calendar:family"
)
when {
    context.dataSubjects.contains("child-a")
};
"""


class CedarGuardConformanceTests(unittest.TestCase):
    def guard(self, policies: str) -> CedarGuard:
        return CedarGuard(
            policies,
            policy_version="test-policy-v1",
            clock=fixed_clock,
        )

    def test_recognized_calendar_create_with_grant_is_allowed(self) -> None:
        decision = self.guard(CALENDAR_GRANT).authorize(request())

        self.assertEqual(decision.effect, GuardEffect.ALLOW)
        self.assertEqual(decision.reason_code, "matching_grant")
        self.assertEqual(decision.matched_rule_ids, ("grant-school-calendar",))
        self.assertEqual(decision.policy_version, "test-policy-v1")

    def test_same_create_without_grant_is_default_denied(self) -> None:
        decision = self.guard("").authorize(request())

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_explicit_deny_overrides_broad_allow(self) -> None:
        decision = self.guard(DENY_OVERRIDE).authorize(
            request(purpose="private-medical")
        )

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "explicit_deny")
        self.assertEqual(
            decision.matched_rule_ids,
            ("deny-private-calendar-create",),
        )

    def test_direct_authenticated_instruction_can_approve_one_off(self) -> None:
        decision = self.guard(EMAIL_APPROVAL).authorize(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                channel="email",
                assurance=AuthenticationAssurance.AUTHENTICATED,
            )
        )

        self.assertEqual(decision.effect, GuardEffect.ALLOW)

    def test_forwarded_instruction_cannot_approve(self) -> None:
        decision = self.guard(EMAIL_APPROVAL).authorize(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=InstructionProvenance.FORWARDED,
                channel="email",
                assurance=AuthenticationAssurance.AUTHENTICATED,
            )
        )

        self.assertEqual(decision.effect, GuardEffect.DENY)

    def test_model_supplied_permission_cannot_approve(self) -> None:
        decision = self.guard(LOCAL_APPROVAL).authorize(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=InstructionProvenance.MODEL,
            )
        )

        self.assertEqual(decision.effect, GuardEffect.DENY)

    def test_expired_or_revoked_grants_do_not_authorize(self) -> None:
        expired = self.guard(EXPIRED_GRANT).authorize(request())
        revoked = self.guard("").authorize(request())

        self.assertEqual(expired.effect, GuardEffect.DENY)
        self.assertEqual(revoked.effect, GuardEffect.DENY)

    def test_busy_time_allowed_but_private_details_denied(self) -> None:
        guard = self.guard(DISCLOSURE_POLICIES)

        busy = guard.authorize(
            request(
                action="calendar.disclose.busy",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            )
        )
        detail = guard.authorize(
            request(
                action="calendar.disclose.detail",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            )
        )

        self.assertEqual(busy.effect, GuardEffect.ALLOW)
        self.assertEqual(detail.effect, GuardEffect.DENY)
        self.assertEqual(detail.reason_code, "explicit_deny")
        self.assertEqual(
            detail.matched_rule_ids,
            ("deny-private-detail-to-family",),
        )

    def test_invalid_request_fails_closed(self) -> None:
        decision = self.guard(CALENDAR_GRANT).authorize(request(actor=""))

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "invalid_request")

    def test_unknown_provenance_fails_closed(self) -> None:
        decision = self.guard(CALENDAR_GRANT).authorize(
            request(provenance="direct from model")
        )

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "invalid_request")

    def test_invalid_policy_schema_combination_is_rejected(self) -> None:
        schema = """
        entity Actor;
        entity AdaResource;
        action "calendar.create" appliesTo {
            principal: Actor,
            resource: AdaResource,
            context: { value: String }
        };
        """
        policies = """
        @id("bad-policy")
        permit(principal, action, resource)
        when { context.value > 5 };
        """

        with self.assertRaises(ValueError):
            CedarGuard(
                policies,
                policy_version="bad",
                schema_text=schema,
                clock=fixed_clock,
            )

    def test_adapter_failure_fails_closed(self) -> None:
        guard = self.guard(CALENDAR_GRANT)

        with patch(
            "ada.adapters.cedar_guard.is_authorized",
            side_effect=RuntimeError("simulated Cedar failure"),
        ):
            decision = guard.authorize(request())

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "cedar_error")

    def test_data_subjects_are_available_to_policy(self) -> None:
        guard = self.guard(SUBJECT_SCOPED_POLICY)

        allowed = guard.authorize(request(data_subjects=("child-a",)))
        denied = guard.authorize(request(data_subjects=("child-b",)))

        self.assertEqual(allowed.effect, GuardEffect.ALLOW)
        self.assertEqual(denied.effect, GuardEffect.DENY)

    def test_naive_guard_clock_fails_closed(self) -> None:
        guard = CedarGuard(
            CALENDAR_GRANT,
            policy_version="test-policy-v1",
            clock=lambda: datetime(2026, 9, 20, 8, 0),
        )

        decision = guard.authorize(request())

        self.assertEqual(decision.effect, GuardEffect.DENY)
        self.assertEqual(decision.reason_code, "invalid_guard_clock")


if __name__ == "__main__":
    unittest.main()
