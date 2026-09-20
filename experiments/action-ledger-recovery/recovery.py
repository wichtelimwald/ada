from __future__ import annotations

from ledger import Ledger
from provider import FakeProvider


def recover_one(ledger: Ledger, provider: FakeProvider, operation_id: str) -> str:
    op = ledger.get(operation_id)

    if op.state == "authorized":
        ledger.transition(operation_id, "authorized", "executing")
        provider_result = provider.create(operation_id)
        if provider_result.committed:
            ledger.transition(
                operation_id,
                "executing",
                "committed",
                provider_reference=provider_result.provider_reference,
            )
            return "committed"
        ledger.transition(operation_id, "executing", "failed")
        return "failed"

    if op.state in {"executing", "ambiguous"}:
        result = provider.reconcile(operation_id)
        if result is None:
            if op.state == "executing":
                ledger.transition(operation_id, "executing", "ambiguous")
            return "ambiguous"
        if result.committed:
            ledger.transition(
                operation_id,
                op.state,
                "committed",
                provider_reference=result.provider_reference,
            )
            return "committed"
        ledger.transition(operation_id, op.state, "failed")
        return "failed"

    return op.state
