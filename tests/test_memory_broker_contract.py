from __future__ import annotations

from dataclasses import fields
import typing
import unittest

from ada.adapters.in_memory_memory_broker import (
    InMemoryMemoryBroker,
    MemoryBrokerConfigurationError,
    MemoryScopeBinding,
)
from ada.core.memory_access import (
    MemoryAccessContext,
    MemoryAccessOperation,
    MemoryScope,
    ProtectionDomainKind,
    ProtectionDomainRef,
)
from ada.ports.memory_broker import MemoryBrokerPort, MemoryScopeDeniedError


def _domain(hex_digit: str, kind: ProtectionDomainKind) -> ProtectionDomainRef:
    return ProtectionDomainRef(
        domain_id=f"pd-{hex_digit * 32}",
        kind=kind,
    )


class MemoryBrokerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private = _domain("1", ProtectionDomainKind.PERSON_PRIVATE)
        self.shared = _domain("2", ProtectionDomainKind.FAMILY_SHARED)
        self.other_private = _domain("3", ProtectionDomainKind.PERSON_PRIVATE)
        self.self_read = MemoryAccessContext(
            actor_ref="actor-a",
            audience_ref="audience-self",
            authorization_ref="auth-memory-self-read",
            operation=MemoryAccessOperation.READ_CURRENT,
        )
        self.family_read = MemoryAccessContext(
            actor_ref="actor-a",
            audience_ref="audience-family",
            authorization_ref="auth-memory-family-read",
            operation=MemoryAccessOperation.READ_CURRENT,
        )
        self.broker = InMemoryMemoryBroker(
            (
                MemoryScopeBinding(
                    context=self.self_read,
                    domains=(self.shared, self.private),
                ),
                MemoryScopeBinding(
                    context=self.family_read,
                    domains=(self.shared,),
                ),
            )
        )

    def test_exact_context_resolves_only_configured_domains(self) -> None:
        scope = self.broker.resolve_scope(self.self_read)

        self.assertEqual(
            tuple(domain.domain_id for domain in scope.domains),
            (self.private.domain_id, self.shared.domain_id),
        )

    def test_family_audience_does_not_inherit_private_scope(self) -> None:
        scope = self.broker.resolve_scope(self.family_read)

        self.assertEqual(scope.domains, (self.shared,))

    def test_each_context_dimension_is_fail_closed(self) -> None:
        variants = (
            MemoryAccessContext(
                actor_ref="actor-b",
                audience_ref=self.self_read.audience_ref,
                authorization_ref=self.self_read.authorization_ref,
                operation=self.self_read.operation,
            ),
            MemoryAccessContext(
                actor_ref=self.self_read.actor_ref,
                audience_ref="audience-family",
                authorization_ref=self.self_read.authorization_ref,
                operation=self.self_read.operation,
            ),
            MemoryAccessContext(
                actor_ref=self.self_read.actor_ref,
                audience_ref=self.self_read.audience_ref,
                authorization_ref="auth-other",
                operation=self.self_read.operation,
            ),
            MemoryAccessContext(
                actor_ref=self.self_read.actor_ref,
                audience_ref=self.self_read.audience_ref,
                authorization_ref=self.self_read.authorization_ref,
                operation=MemoryAccessOperation.WRITE_CURRENT,
            ),
        )

        for context in variants:
            with self.subTest(context=context):
                with self.assertRaises(MemoryScopeDeniedError):
                    self.broker.resolve_scope(context)

    def test_request_context_has_no_caller_selectable_domain(self) -> None:
        self.assertEqual(
            {field.name for field in fields(MemoryAccessContext)},
            {"actor_ref", "audience_ref", "authorization_ref", "operation"},
        )

    def test_domain_reference_exposes_no_storage_or_secret_material(self) -> None:
        self.assertEqual(
            {field.name for field in fields(ProtectionDomainRef)},
            {"domain_id", "kind"},
        )
        self.assertFalse(hasattr(self.private, "root"))
        self.assertFalse(hasattr(self.private, "key"))
        self.assertFalse(hasattr(self.private, "credential"))

    def test_domain_ids_must_be_opaque(self) -> None:
        with self.assertRaises(ValueError):
            ProtectionDomainRef(
                domain_id="parent-a-private",
                kind=ProtectionDomainKind.PERSON_PRIVATE,
            )

    def test_empty_and_duplicate_scopes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MemoryScope(())
        with self.assertRaises(ValueError):
            MemoryScope((self.private, self.private))

    def test_duplicate_context_binding_is_rejected(self) -> None:
        with self.assertRaises(MemoryBrokerConfigurationError):
            InMemoryMemoryBroker(
                (
                    MemoryScopeBinding(self.self_read, (self.private,)),
                    MemoryScopeBinding(self.self_read, (self.shared,)),
                )
            )

    def test_one_domain_id_cannot_change_kind_across_bindings(self) -> None:
        conflicting = ProtectionDomainRef(
            domain_id=self.private.domain_id,
            kind=ProtectionDomainKind.FAMILY_SHARED,
        )
        with self.assertRaises(MemoryBrokerConfigurationError):
            InMemoryMemoryBroker(
                (
                    MemoryScopeBinding(self.self_read, (self.private,)),
                    MemoryScopeBinding(self.family_read, (conflicting,)),
                )
            )

    def test_unrelated_private_domain_cannot_be_requested(self) -> None:
        scope = self.broker.resolve_scope(self.self_read)

        self.assertNotIn(self.other_private, scope.domains)

    def test_resolve_scope_is_keyed_only_by_trusted_context_not_by_scope(
        self,
    ) -> None:
        """Guard PR #46 finding M1: the broker port must take a trusted
        MemoryAccessContext as its only input, never a caller-supplied
        MemoryScope/domain ID that could be replayed as an authorization
        capability."""
        hints = typing.get_type_hints(MemoryBrokerPort.resolve_scope)
        parameter_hints = {
            name: hint for name, hint in hints.items() if name != "return"
        }

        self.assertEqual(parameter_hints, {"context": MemoryAccessContext})

    def test_caller_constructed_scope_cannot_be_presented_to_the_broker(
        self,
    ) -> None:
        """A caller can freely build a MemoryScope naming any configured
        domain, but the broker only recognizes a trusted MemoryAccessContext:
        presenting a forged scope where a context is expected still fails
        closed rather than being accepted as proof of access."""
        forged = MemoryScope((self.private, self.shared))

        with self.assertRaises(MemoryScopeDeniedError):
            self.broker.resolve_scope(forged)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
