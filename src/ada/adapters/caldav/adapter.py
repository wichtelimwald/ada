from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx2

from ada.adapters.caldav import dav_client, mapping
from ada.adapters.caldav.dav_client import (
    CalDAVAmbiguousTransportError,
    CalDAVConfigurationError,
    CalDAVNotAttemptedError,
    CalDAVProtocolError,
    CalDAVResponseTooLargeError,
    CalDAVUnsafeXmlError,
    CollectionInfo,
)
from ada.adapters.caldav.mapping import (
    CalDAVMappingError,
    CalendarComplexityExceededError,
    WriteScopeError,
)
from ada.adapters.caldav.profile import CalDAVProviderProfile
from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import (
    CancelCalendarEventProposal,
    CreateCalendarEventProposal,
    EventRef,
    EventVersion,
    UpdateCalendarEventProposal,
)
from ada.ports.calendar import (
    CalendarAccessMode,
    CalendarChangeResult,
    CalendarChangeStatus,
    CalendarCreateResult,
    CalendarCreateStatus,
    CalendarEvent,
    CalendarRef,
)


if TYPE_CHECKING:
    import icalendar


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Errors that mean "Ada could not read back/verify a resource", never
# "nothing happened" or "prove a stronger outcome". They are caught around
# post-write verification (a GET/parse after an already-sent PUT) so a
# transport hiccup or a malformed read-back never escapes the typed
# CalendarCreateResult/CalendarEvent contract as a raw exception; the caller
# already has provider evidence (a status code) and must keep reporting only
# what that evidence supports (ADR-0005), not crash the durable workflow.
_RECOVERABLE_VERIFICATION_ERRORS = (
    CalDAVNotAttemptedError,
    CalDAVAmbiguousTransportError,
    CalDAVProtocolError,
    CalDAVResponseTooLargeError,
    CalDAVUnsafeXmlError,
    CalDAVMappingError,
    CalendarComplexityExceededError,
)


class CalDAVCalendarAdapter:
    """Generic CalDAV ``CalendarPort`` adapter driven by a declarative profile.

    ADR-0009 section 2: one adapter for every CalDAV provider; provider
    differences live entirely in the injected :class:`CalDAVProviderProfile`
    and the configured :class:`CalendarRef` entries, never in adapter code.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth: tuple[str, str],
        calendars: Sequence[CalendarRef],
        profile: CalDAVProviderProfile,
        transport: httpx2.BaseTransport | None = None,
        timeout_seconds: float = 15.0,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not calendars:
            raise CalDAVConfigurationError(
                "at least one CalendarRef must be configured"
            )

        self._base_url = base_url
        self._profile = profile
        self._clock = clock
        self._calendars: dict[str, CalendarRef] = {
            ref.calendar_id: ref for ref in calendars
        }
        self._client = dav_client.build_client(
            base_url=base_url,
            auth=auth,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._collection_cache: dict[str, CollectionInfo] = {}

    @property
    def create_capability(self) -> ProviderCapability:
        return self._profile.create_capability

    @property
    def update_capability(self) -> ProviderCapability:
        return self._profile.update_capability

    @property
    def cancel_capability(self) -> ProviderCapability:
        return self._profile.cancel_capability

    def close(self) -> None:
        self._client.close()

    def _resolve_collection(self, ref: CalendarRef) -> CollectionInfo:
        cached = self._collection_cache.get(ref.calendar_id)
        if cached is not None:
            return cached

        info = dav_client.propfind_collection(
            self._client,
            base_url=self._base_url,
            collection_path=ref.provider_collection,
            max_response_bytes=self._profile.max_response_bytes,
        )
        self._collection_cache[ref.calendar_id] = info
        return info

    def _intersect_window(
        self, start: datetime, end: datetime
    ) -> tuple[datetime, datetime] | None:
        """The intersection of ``[start, end)`` with the profile's supported
        query window around "now", or ``None`` when they do not overlap at
        all (for example a request entirely before or after the provider's
        supported range). Clamping only the individual bounds and repairing
        an inverted result afterward can silently produce a *non-empty*
        interval that still lies entirely outside the supported window
        (for example ``[+400d, +400d]`` when the ceiling is ``+365d``); an
        explicit intersection avoids that by construction.
        """

        now = self._clock()
        floor = now - self._profile.query_window_before
        ceiling = now + self._profile.query_window_after

        intersection_start = max(start, floor)
        intersection_end = min(end, ceiling)
        if intersection_start >= intersection_end:
            return None
        return intersection_start, intersection_end

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[CalendarEvent]:
        window = self._intersect_window(start, end)
        if window is None:
            # No overlap with the provider-supported window at all: no
            # collection needs to be resolved and no REPORT needs to be sent.
            return ()
        clamped_start, clamped_end = window

        events: list[CalendarEvent] = []
        # Per-query budget: shared across every collection queried by this
        # call, decremented as each resource is mapped, and passed *into*
        # the mapper so it is enforced before that resource's own
        # recurrence expansion runs (ADR-0009 section 5).
        occurrences_remaining = self._profile.max_occurrences_per_query

        for ref in self._calendars.values():
            collection = self._resolve_collection(ref)
            entries = dav_client.calendar_query(
                self._client,
                base_url=self._base_url,
                collection_href=collection.href,
                start=clamped_start,
                end=clamped_end,
                max_response_bytes=self._profile.max_response_bytes,
            )

            # Component/property limits are per response (one REPORT call,
            # i.e. one collection); the occurrence limit is per query (the
            # whole list_events call, matching ADR-0009 section 5).
            components_remaining = self._profile.max_components_per_response

            for entry in entries:
                resource_name = entry.href.rsplit("/", 1)[-1]
                mapped = mapping.map_resource_occurrences(
                    calendar_id=ref.calendar_id,
                    resource_name=resource_name,
                    calendar_data=entry.calendar_data,
                    version=EventVersion(entry.etag) if entry.etag else None,
                    window_start=clamped_start,
                    window_end=clamped_end,
                    max_properties_per_component=(
                        self._profile.max_properties_per_component
                    ),
                    max_occurrences_per_series=(
                        self._profile.max_occurrences_per_series
                    ),
                    remaining_component_budget=components_remaining,
                    remaining_occurrence_budget=occurrences_remaining,
                )

                components_remaining -= mapped.component_count
                occurrences_remaining -= len(mapped.events)
                events.extend(mapped.events)

        return tuple(
            event for event in events if event.start < end and event.end > start
        )

    def create_event(
        self,
        proposal: CreateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarCreateResult:
        ref = self._calendars.get(proposal.calendar_id)
        if ref is None:
            return CalendarCreateResult(
                status=CalendarCreateStatus.REJECTED,
                error_code="calendar_not_configured",
            )
        if ref.access_mode is not CalendarAccessMode.WRITE:
            return CalendarCreateResult(
                status=CalendarCreateStatus.REJECTED,
                error_code="calendar_not_writable",
            )

        collection = self._resolve_collection(ref)
        marker = mapping.derive_operation_marker(operation_id)
        resource_name = mapping.derive_resource_name(operation_id)
        resource_href = f"{collection.href.rstrip('/')}/{resource_name}"
        uid = mapping.derive_event_uid(operation_id)

        body = mapping.build_create_ical(proposal, uid=uid, marker=marker)

        try:
            response = dav_client.put_create_only(
                self._client,
                resource_href,
                body=body,
                max_response_bytes=self._profile.max_response_bytes,
            )
        except CalDAVNotAttemptedError:
            return CalendarCreateResult(
                status=CalendarCreateStatus.REJECTED,
                error_code="not_attempted",
            )
        except CalDAVAmbiguousTransportError:
            return CalendarCreateResult(
                status=CalendarCreateStatus.AMBIGUOUS,
                error_code="ambiguous_transport",
            )

        if response.status_code in (200, 201, 204):
            # ADR-0009 section 6: "Any 2xx status is success" -- the write is
            # already proven, unconditionally. Read-back only verifies/
            # enriches the stored version; it must never downgrade an
            # already-known commit to ambiguous, whether it fails outright or
            # (unexpectedly) reports the resource missing. But the provider
            # owns events: without a successful read-back Ada must not report
            # its own proposal as if it were verified provider state, only
            # the deterministic reference it already knows.
            event_ref = EventRef(
                calendar_id=ref.calendar_id, resource_name=resource_name
            )
            try:
                event = self._read_back(ref.calendar_id, resource_href, resource_name)
            except _RECOVERABLE_VERIFICATION_ERRORS:
                event = None
            return CalendarCreateResult(
                status=CalendarCreateStatus.COMMITTED,
                event_ref=event_ref,
                event=event,
            )

        if response.status_code == 412:
            existing = self._safe_reconcile_via_marker(
                ref.calendar_id, resource_href, resource_name, marker
            )
            if existing is not None:
                return CalendarCreateResult(
                    status=CalendarCreateStatus.COMMITTED,
                    event_ref=EventRef(
                        calendar_id=ref.calendar_id, resource_name=resource_name
                    ),
                    event=existing,
                )
            return CalendarCreateResult(
                status=CalendarCreateStatus.AMBIGUOUS,
                error_code="precondition_failed_unresolved",
            )

        if response.status_code == 403:
            # Duplicate UID under a different resource name. Under normal
            # operation this cannot happen (both are derived deterministically
            # from the same operation_id); Ada cannot safely resolve it
            # without a UID-based search, which is out of MVP scope. This
            # intentionally does not attempt a GET-based reconciliation.
            return CalendarCreateResult(
                status=CalendarCreateStatus.AMBIGUOUS,
                error_code="duplicate_uid_conflict",
            )

        return CalendarCreateResult(
            status=CalendarCreateStatus.AMBIGUOUS,
            error_code=f"unexpected_status_{response.status_code}",
        )

    def reconcile_create(self, *, operation_id: str) -> CalendarEvent | None:
        marker = mapping.derive_operation_marker(operation_id)
        resource_name = mapping.derive_resource_name(operation_id)

        for ref in self._calendars.values():
            if ref.access_mode is not CalendarAccessMode.WRITE:
                continue
            collection = self._resolve_collection(ref)
            resource_href = f"{collection.href.rstrip('/')}/{resource_name}"
            existing = self._safe_reconcile_via_marker(
                ref.calendar_id, resource_href, resource_name, marker
            )
            if existing is not None:
                return existing
        return None

    def _read_back(
        self, calendar_id: str, resource_href: str, resource_name: str
    ) -> CalendarEvent | None:
        result = dav_client.get_resource(
            self._client,
            resource_href,
            max_response_bytes=self._profile.max_response_bytes,
        )
        if result is None:
            return None
        return mapping.map_single_event(
            calendar_id=calendar_id,
            resource_name=resource_name,
            calendar_data=result.calendar_data,
            version=EventVersion(result.etag) if result.etag else None,
        )

    def _safe_reconcile_via_marker(
        self,
        calendar_id: str,
        resource_href: str,
        resource_name: str,
        marker: str,
    ) -> CalendarEvent | None:
        """As :meth:`_reconcile_via_marker`, but never lets an exception escape.

        The port contract for this call is "prove a commit or say you
        can't"; a transport/parsing failure while trying to prove it is
        exactly the "can't" case, not a reason to crash the caller.
        """

        try:
            return self._reconcile_via_marker(
                calendar_id, resource_href, resource_name, marker
            )
        except _RECOVERABLE_VERIFICATION_ERRORS:
            return None

    def _reconcile_via_marker(
        self,
        calendar_id: str,
        resource_href: str,
        resource_name: str,
        marker: str,
    ) -> CalendarEvent | None:
        if not self._profile.preserves_x_properties:
            # Without a preserved marker Ada cannot prove the resource is its
            # own write; do not guess.
            return None

        result = dav_client.get_resource(
            self._client,
            resource_href,
            max_response_bytes=self._profile.max_response_bytes,
        )
        if result is None:
            return None

        component = mapping.parse_single_vevent(
            result.calendar_data, resource_name=resource_name
        )
        if mapping.component_operation_marker(component) != marker:
            return None

        return mapping.build_calendar_event_from_component(
            component,
            calendar_id=calendar_id,
            resource_name=resource_name,
            version=EventVersion(result.etag) if result.etag else None,
        )

    # -- update / cancel (ADR-0009 section 6) -------------------------------

    def update_event(
        self,
        proposal: UpdateCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        return self._change_event(proposal, operation_id=operation_id)

    def cancel_event(
        self,
        proposal: CancelCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        return self._change_event(proposal, operation_id=operation_id)

    def _change_event(
        self,
        proposal: UpdateCalendarEventProposal | CancelCalendarEventProposal,
        *,
        operation_id: str,
    ) -> CalendarChangeResult:
        """One conditional update or cancel.

        Fails closed before any provider request for an unconfigured or
        read-only calendar. Then: read the resource; a replay that finds this
        operation's marker is already committed; a version other than
        ``base_version`` is a conflict and nothing is written; otherwise write
        with ``If-Match: <base_version>`` only, never a later-read tag.
        """

        is_update = isinstance(proposal, UpdateCalendarEventProposal)
        event_ref = proposal.event_ref
        ref = self._calendars.get(event_ref.calendar_id)
        if ref is None:
            return _change_result(
                CalendarChangeStatus.REJECTED, "calendar_not_configured"
            )
        if ref.access_mode is not CalendarAccessMode.WRITE:
            return _change_result(
                CalendarChangeStatus.REJECTED, "calendar_not_writable"
            )
        name = event_ref.resource_name
        if name.startswith(".") or any(ch in name for ch in "/\\?#%"):
            return _change_result(
                CalendarChangeStatus.REJECTED, "invalid_resource_name"
            )

        marker = mapping.derive_operation_marker(operation_id)
        base_etag = dav_client.normalize_etag(str(proposal.base_version.version))

        try:
            collection = self._resolve_collection(ref)
            href = f"{collection.href.rstrip('/')}/{name}"
            current = dav_client.get_resource(
                self._client,
                href,
                max_response_bytes=self._profile.max_response_bytes,
            )
            if current is None:
                return _change_result(CalendarChangeStatus.ABSENT, "event_absent")
            component = mapping.parse_writable_vevent(
                current.calendar_data, resource_name=name
            )
        except WriteScopeError as exc:
            return _change_result(CalendarChangeStatus.REJECTED, exc.code)
        except _RECOVERABLE_VERIFICATION_ERRORS:
            # Nothing has been written yet; only reads failed.
            return _change_result(CalendarChangeStatus.REJECTED, "pre_read_failed")

        if is_update and self._owns(component, marker):
            # A replay after a lost checkpoint/response: this operation
            # already applied. Checked before the version comparison, which
            # our own write necessarily changed.
            return CalendarChangeResult(
                status=CalendarChangeStatus.COMMITTED,
                event_ref=event_ref,
                event=self._event_from(ref, name, component, current.etag),
            )

        if current.etag is None:
            return _change_result(CalendarChangeStatus.REJECTED, "version_unavailable")
        if (
            current.etag != base_etag
            or mapping.component_sequence(component)
            != proposal.base_version.sequence
        ):
            return _change_result(CalendarChangeStatus.CONFLICT, "version_conflict")

        try:
            if isinstance(proposal, UpdateCalendarEventProposal):
                response = dav_client.put_conditional(
                    self._client,
                    href,
                    body=mapping.build_update_ical(
                        current.calendar_data, proposal, marker=marker
                    ),
                    if_match=base_etag,
                    max_response_bytes=self._profile.max_response_bytes,
                )
            else:
                response = dav_client.delete_conditional(
                    self._client,
                    href,
                    if_match=base_etag,
                    max_response_bytes=self._profile.max_response_bytes,
                )
        except WriteScopeError as exc:
            return _change_result(CalendarChangeStatus.REJECTED, exc.code)
        except CalDAVMappingError:
            return _change_result(CalendarChangeStatus.REJECTED, "unsupported_event")
        except CalDAVNotAttemptedError:
            return _change_result(CalendarChangeStatus.REJECTED, "not_attempted")
        except CalDAVAmbiguousTransportError:
            return self._reconcile_change(
                ref, name, href, marker, base_etag, is_update=is_update
            )

        if response.status_code in (200, 201, 204):
            event: CalendarEvent | None = None
            if is_update:
                try:
                    event = self._read_back(ref.calendar_id, href, name)
                except _RECOVERABLE_VERIFICATION_ERRORS:
                    event = None
            return CalendarChangeResult(
                status=CalendarChangeStatus.COMMITTED,
                event_ref=event_ref,
                event=event,
            )
        if response.status_code == 412:
            return _change_result(CalendarChangeStatus.CONFLICT, "version_conflict")
        if response.status_code == 404:
            return _change_result(CalendarChangeStatus.ABSENT, "event_absent")
        return self._reconcile_change(
            ref, name, href, marker, base_etag, is_update=is_update
        )

    def _owns(self, component: "icalendar.cal.Component", marker: str) -> bool:
        return (
            self._profile.preserves_x_properties
            and mapping.component_operation_marker(component) == marker
        )

    def _event_from(
        self,
        ref: CalendarRef,
        name: str,
        component: "icalendar.cal.Component",
        etag: str | None,
    ) -> CalendarEvent | None:
        try:
            return mapping.build_calendar_event_from_component(
                component,
                calendar_id=ref.calendar_id,
                resource_name=name,
                version=EventVersion(etag) if etag else None,
            )
        except _RECOVERABLE_VERIFICATION_ERRORS:
            return None

    def _reconcile_change(
        self,
        ref: CalendarRef,
        name: str,
        href: str,
        marker: str,
        base_etag: str,
        *,
        is_update: bool,
    ) -> CalendarChangeResult:
        """Re-read after an ambiguous send. The re-read is evidence, not a
        verdict: only this operation's marker proves an update, an unchanged
        base proves nothing was applied, and anything else stays ambiguous."""

        try:
            current = dav_client.get_resource(
                self._client,
                href,
                max_response_bytes=self._profile.max_response_bytes,
            )
            if current is None:
                return _change_result(CalendarChangeStatus.ABSENT, "event_absent")
            component = mapping.parse_single_vevent(
                current.calendar_data, resource_name=name
            )
        except _RECOVERABLE_VERIFICATION_ERRORS:
            return _change_result(
                CalendarChangeStatus.AMBIGUOUS, "reconciliation_failed"
            )

        if is_update and self._owns(component, marker):
            return CalendarChangeResult(
                status=CalendarChangeStatus.COMMITTED,
                event_ref=EventRef(calendar_id=ref.calendar_id, resource_name=name),
                event=self._event_from(ref, name, component, current.etag),
            )
        if current.etag == base_etag:
            return _change_result(CalendarChangeStatus.NOT_APPLIED, "not_applied")
        return _change_result(
            CalendarChangeStatus.AMBIGUOUS, "changed_after_ambiguous_send"
        )


def _change_result(
    status: CalendarChangeStatus, error_code: str
) -> CalendarChangeResult:
    return CalendarChangeResult(status=status, error_code=error_code)
