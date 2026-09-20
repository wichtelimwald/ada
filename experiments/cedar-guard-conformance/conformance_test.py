from __future__ import annotations

import unittest

from cedar_adapter import (
    Assurance,
    AuthorizationRequest,
    CedarGuard,
    Effect,
    Provenance,
)


NOW_MS = 1_779_000_000_000


def req(**changes: object) -> AuthorizationRequest:
    values: dict[str, object] = {
        "actor": "guardian-a",
        "action": "calendar.create",
        "resource": "calendar:family",
        "data_subjects": ("child-a",),
        "audience": "family",
        "purpose": "family-coordination",
        "provenance": Provenance.DIRECT,
        "channel": "local-chat",
        "assurance": Assurance.LOCAL_TRUSTED,
        "acting_for": None,
        "now_epoch_ms": NOW_MS,
    }
    values.update(changes)
    return AuthorizationRequest(**values)


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


class CedarGuardConformanceTests(unittest.TestCase):
    def test_01_recognized_calendar_create_with_grant_is_allowed(self) -> None:
        decision = CedarGuard(CALENDAR_GRANT).authorize(req())

        self.assertEqual(decision.effect, Effect.ALLOW)
        self.assertEqual(decision.reason_code, "matching_grant")
        self.assertEqual(decision.matched_rule_ids, ("grant-school-calendar",))
        self.assertEqual(decision.policy_version, "prototype-v1")

    def test_02_same_create_without_grant_is_default_denied(self) -> None:
        decision = CedarGuard("").authorize(req())

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_03_explicit_deny_overrides_broad_allow(self) -> None:
        decision = CedarGuard(DENY_OVERRIDE).authorize(
            req(purpose="private-medical")
        )

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "explicit_deny")
        self.assertEqual(
            decision.matched_rule_ids,
            ("deny-private-calendar-create",),
        )

    def test_04_direct_authenticated_instruction_can_approve_one_off(self) -> None:
        decision = CedarGuard(EMAIL_APPROVAL).authorize(
            req(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                channel="email",
                assurance=Assurance.AUTHENTICATED,
            )
        )

        self.assertEqual(decision.effect, Effect.ALLOW)

    def test_05_forwarded_instruction_cannot_approve(self) -> None:
        decision = CedarGuard(EMAIL_APPROVAL).authorize(
            req(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=Provenance.FORWARDED,
                channel="email",
                assurance=Assurance.AUTHENTICATED,
            )
        )

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_06_model_supplied_permission_cannot_approve(self) -> None:
        decision = CedarGuard(LOCAL_APPROVAL).authorize(
            req(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=Provenance.MODEL,
            )
        )

        self.assertEqual(decision.effect, Effect.DENY)

    def test_07_expired_or_revoked_grants_do_not_authorize(self) -> None:
        expired = CedarGuard(EXPIRED_GRANT).authorize(req())
        # Revocation is grant-store lifecycle: a revoked grant is removed from
        # the active policy set before authorization.
        revoked = CedarGuard("").authorize(req())

        self.assertEqual(expired.effect, Effect.DENY)
        self.assertEqual(revoked.effect, Effect.DENY)

    def test_08_busy_time_allowed_but_private_details_denied(self) -> None:
        guard = CedarGuard(DISCLOSURE_POLICIES)

        busy = guard.authorize(
            req(
                action="calendar.disclose.busy",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            )
        )
        detail = guard.authorize(
            req(
                action="calendar.disclose.detail",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            )
        )

        self.assertEqual(busy.effect, Effect.ALLOW)
        self.assertEqual(detail.effect, Effect.DENY)
        self.assertEqual(detail.reason_code, "explicit_deny")
        self.assertEqual(
            detail.matched_rule_ids,
            ("deny-private-detail-to-family",),
        )

    def test_09_invalid_request_fails_closed(self) -> None:
        decision = CedarGuard(CALENDAR_GRANT).authorize(req(actor=""))

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "invalid_request")

    def test_10_cedar_policy_evaluation_error_fails_closed(self) -> None:
        # Without schema validation, Cedar can legitimately produce Allow from
        # one policy while another policy errors. Ada must be stricter.
        unsafe_schema = """
        entity Actor;
        entity AdaResource;
        action "calendar.create" appliesTo {
            principal: Actor,
            resource: AdaResource,
            context: { value: String }
        };
        """
        policies = """
        @id("good-permit")
        permit(principal, action, resource);

        @id("bad-policy")
        permit(principal, action, resource)
        when { context.value > 5 };
        """

        # The production constructor validates and correctly rejects this
        # policy set up-front.
        with self.assertRaises(ValueError):
            CedarGuard(policies, schema_text=unsafe_schema)


if __name__ == "__main__":
    unittest.main()
