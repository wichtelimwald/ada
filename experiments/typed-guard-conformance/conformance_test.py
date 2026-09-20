from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from evaluator import (
    Assurance,
    AuthorizationRequest,
    Effect,
    Provenance,
    Rule,
    evaluate,
)


NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


def request(
    *,
    actor: str = "guardian-a",
    action: str = "calendar.create",
    resource: str = "calendar:family",
    data_subjects: tuple[str, ...] = ("child-a",),
    audience: str | None = "family",
    purpose: str | None = "family-coordination",
    provenance: Provenance = Provenance.DIRECT,
    channel: str = "local-chat",
    assurance: Assurance = Assurance.LOCAL_TRUSTED,
    acting_for: str | None = None,
) -> AuthorizationRequest:
    return AuthorizationRequest(
        actor=actor,
        action=action,
        resource=resource,
        data_subjects=data_subjects,
        audience=audience,
        purpose=purpose,
        provenance=provenance,
        channel=channel,
        assurance=assurance,
        acting_for=acting_for,
        now=NOW,
    )


class GuardConformanceTests(unittest.TestCase):
    def test_01_recognized_calendar_create_with_grant_is_allowed(self) -> None:
        rules = [
            Rule(
                rule_id="grant-school-calendar",
                effect=Effect.ALLOW,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"calendar.create"}),
                resources=frozenset({"calendar:family"}),
                provenances=frozenset({Provenance.DIRECT}),
                min_assurance=Assurance.AUTHENTICATED,
            )
        ]

        decision = evaluate(request(), rules)

        self.assertEqual(decision.effect, Effect.ALLOW)
        self.assertEqual(decision.reason_code, "matching_grant")
        self.assertEqual(decision.matched_rule_ids, ("grant-school-calendar",))
        self.assertEqual(decision.policy_version, "prototype-v1")

    def test_02_same_create_without_grant_is_default_denied(self) -> None:
        decision = evaluate(request(), [])

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_03_explicit_deny_overrides_broad_allow(self) -> None:
        rules = [
            Rule(
                rule_id="grant-family-calendar",
                effect=Effect.ALLOW,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"calendar.create"}),
                resources=frozenset({"calendar:family"}),
            ),
            Rule(
                rule_id="deny-private-calendar-create",
                effect=Effect.DENY,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"calendar.create"}),
                resources=frozenset({"calendar:family"}),
                purposes=frozenset({"private-medical"}),
            ),
        ]

        decision = evaluate(request(purpose="private-medical"), rules)

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "explicit_deny")
        self.assertEqual(
            decision.matched_rule_ids,
            ("deny-private-calendar-create",),
        )

    def test_04_direct_authenticated_instruction_can_approve_one_off_action(self) -> None:
        rules = [
            Rule(
                rule_id="one-off-email-approval",
                effect=Effect.ALLOW,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"approval.simple"}),
                resources=frozenset({"operation:calendar:123"}),
                provenances=frozenset({Provenance.DIRECT}),
                channels=frozenset({"email"}),
                min_assurance=Assurance.AUTHENTICATED,
            )
        ]

        decision = evaluate(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                channel="email",
                assurance=Assurance.AUTHENTICATED,
            ),
            rules,
        )

        self.assertEqual(decision.effect, Effect.ALLOW)

    def test_05_forwarded_instruction_cannot_approve(self) -> None:
        rules = [
            Rule(
                rule_id="one-off-email-approval",
                effect=Effect.ALLOW,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"approval.simple"}),
                resources=frozenset({"operation:calendar:123"}),
                provenances=frozenset({Provenance.DIRECT}),
                channels=frozenset({"email"}),
                min_assurance=Assurance.AUTHENTICATED,
            )
        ]

        decision = evaluate(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=Provenance.FORWARDED,
                channel="email",
                assurance=Assurance.AUTHENTICATED,
            ),
            rules,
        )

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_06_model_supplied_permission_cannot_approve(self) -> None:
        rules = [
            Rule(
                rule_id="one-off-local-approval",
                effect=Effect.ALLOW,
                actors=frozenset({"guardian-a"}),
                actions=frozenset({"approval.simple"}),
                resources=frozenset({"operation:calendar:123"}),
                provenances=frozenset({Provenance.DIRECT}),
                channels=frozenset({"local-chat"}),
                min_assurance=Assurance.LOCAL_TRUSTED,
            )
        ]

        decision = evaluate(
            request(
                action="approval.simple",
                resource="operation:calendar:123",
                data_subjects=(),
                audience=None,
                purpose="approve-operation",
                provenance=Provenance.MODEL,
            ),
            rules,
        )

        self.assertEqual(decision.effect, Effect.DENY)

    def test_07_revoked_and_expired_grants_stop_authorizing(self) -> None:
        revoked = Rule(
            rule_id="revoked-grant",
            effect=Effect.ALLOW,
            actions=frozenset({"calendar.create"}),
            resources=frozenset({"calendar:family"}),
            revoked=True,
        )
        expired = Rule(
            rule_id="expired-grant",
            effect=Effect.ALLOW,
            actions=frozenset({"calendar.create"}),
            resources=frozenset({"calendar:family"}),
            valid_until=NOW - timedelta(seconds=1),
        )

        decision = evaluate(request(), [revoked, expired])

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "no_matching_grant")

    def test_08_private_busy_time_can_be_shared_but_details_are_denied(self) -> None:
        rules = [
            Rule(
                rule_id="allow-family-busy-view",
                effect=Effect.ALLOW,
                actions=frozenset({"calendar.disclose.busy"}),
                resources=frozenset({"event:parent-a-private"}),
                audiences=frozenset({"family"}),
            ),
            Rule(
                rule_id="allow-family-calendar-read",
                effect=Effect.ALLOW,
                actions=frozenset({"calendar.disclose.detail"}),
                resources=frozenset({"event:parent-a-private"}),
                audiences=frozenset({"family"}),
            ),
            Rule(
                rule_id="deny-private-detail-to-family",
                effect=Effect.DENY,
                actions=frozenset({"calendar.disclose.detail"}),
                resources=frozenset({"event:parent-a-private"}),
                audiences=frozenset({"family"}),
            ),
        ]

        busy = evaluate(
            request(
                action="calendar.disclose.busy",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            ),
            rules,
        )
        detail = evaluate(
            request(
                action="calendar.disclose.detail",
                resource="event:parent-a-private",
                data_subjects=("parent-a",),
                audience="family",
                purpose="daily-briefing",
            ),
            rules,
        )

        self.assertEqual(busy.effect, Effect.ALLOW)
        self.assertEqual(detail.effect, Effect.DENY)
        self.assertEqual(detail.reason_code, "explicit_deny")
        self.assertEqual(
            detail.matched_rule_ids,
            ("deny-private-detail-to-family",),
        )

    def test_09_invalid_request_fails_closed(self) -> None:
        invalid = request(actor="")

        decision = evaluate(invalid, [])

        self.assertEqual(decision.effect, Effect.DENY)
        self.assertEqual(decision.reason_code, "invalid_request")


if __name__ == "__main__":
    unittest.main()
