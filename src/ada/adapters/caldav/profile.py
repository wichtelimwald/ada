from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ada.core.action_outcomes import ProviderCapability


@dataclass(frozen=True, slots=True)
class CalDAVProviderProfile:
    """Declarative, code-free description of one CalDAV provider's behavior.

    ADR-0009 section 2: Ada has one generic CalDAV adapter; differences
    between CalDAV providers are captured as data here, never as adapter
    code. A new CalDAV provider needs a new profile plus passing contract
    tests, not a new adapter.
    """

    name: str

    # Bounded query window the provider is known to answer reliably
    # (evaluation section 3/10). Requests are clamped to this window.
    query_window_before: timedelta
    query_window_after: timedelta

    # Duplicate-safety semantics this provider gives Ada for create.
    create_capability: ProviderCapability

    # Same for update and cancel (ADR-0009 section 2: declared per operation
    # kind). Both are ``If-Match``-conditional; update also relies on the
    # operation marker for reconciliation.
    update_capability: ProviderCapability
    cancel_capability: ProviderCapability

    # Deterministic complexity limits for untrusted calendar data
    # (ADR-0009 section 5). Exceeding any of these fails closed for the
    # affected calendar.
    max_components_per_response: int
    max_properties_per_component: int
    max_occurrences_per_series: int
    max_occurrences_per_query: int

    # Whether the provider is known to preserve unrecognized ``X-`` iCalendar
    # properties on write/read-back (evaluation section 3, probe P3). Without
    # this, Ada's operation marker cannot be trusted as reconciliation
    # evidence.
    preserves_x_properties: bool

    # Maximum response body size accepted from this provider, in bytes.
    max_response_bytes: int


# Evaluation section 10 / ADR-0009: recorded IONOS Mail Business (Open-Xchange)
# behavior from the maintainer's probe runs 1-4, 2026-09-26.
IONOS_PROFILE = CalDAVProviderProfile(
    name="ionos",
    query_window_before=timedelta(days=30),
    query_window_after=timedelta(days=365),
    create_capability=ProviderCapability.IDEMPOTENT,
    update_capability=ProviderCapability.RECONCILABLE,
    cancel_capability=ProviderCapability.IDEMPOTENT,
    max_components_per_response=500,
    max_properties_per_component=200,
    max_occurrences_per_series=1000,
    max_occurrences_per_query=2000,
    preserves_x_properties=True,
    max_response_bytes=2_000_000,
)
