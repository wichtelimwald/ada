from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone

import httpx2

from ada.adapters.caldav import dav_client, mapping
from ada.adapters.caldav.dav_client import (
    CalDAVAmbiguousTransportError,
    CalDAVConfigurationError,
    CalDAVNotAttemptedError,
    CollectionInfo,
)
from ada.adapters.caldav.mapping import CalendarComplexityExceededError
from ada.adapters.caldav.profile import CalDAVProviderProfile
from ada.core.action_outcomes import ProviderCapability
from ada.core.actions import CreateCalendarEventProposal
from ada.ports.calendar import (
    CalendarAccessMode,
    CalendarCreateResult,
    CalendarCreateStatus,
    CalendarEvent,
    CalendarRef,
    EventVersion,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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

    def _clamp_window(
        self, start: datetime, end: datetime
    ) -> tuple[datetime, datetime]:
        now = self._clock()
        floor = now - self._profile.query_window_before
        ceiling = now + self._profile.query_window_after
        clamped_start = max(start, floor)
        clamped_end = min(end, ceiling)
        if clamped_end < clamped_start:
            clamped_end = clamped_start
        return clamped_start, clamped_end

    def list_events(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> Sequence[CalendarEvent]:
        clamped_start, clamped_end = self._clamp_window(start, end)

        events: list[CalendarEvent] = []
        total_occurrences = 0

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
            components_in_this_response = 0

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
                )

                components_in_this_response += mapped.component_count
                if (
                    components_in_this_response
                    > self._profile.max_components_per_response
                ):
                    raise CalendarComplexityExceededError(
                        f"calendar {ref.calendar_id!r} response exceeds the "
                        "per-response component limit"
                    )

                total_occurrences += len(mapped.events)
                if total_occurrences > self._profile.max_occurrences_per_query:
                    raise CalendarComplexityExceededError(
                        f"calendar {ref.calendar_id!r} query exceeds the "
                        "per-query occurrence limit"
                    )

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
                self._client, resource_href, body=body
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
            event = self._read_back(ref.calendar_id, resource_href, resource_name)
            if event is None:
                return CalendarCreateResult(
                    status=CalendarCreateStatus.AMBIGUOUS,
                    error_code="provider_missing_reference",
                )
            return CalendarCreateResult(
                status=CalendarCreateStatus.COMMITTED, event=event
            )

        if response.status_code == 412:
            existing = self._reconcile_via_marker(
                ref.calendar_id, resource_href, resource_name, marker
            )
            if existing is not None:
                return CalendarCreateResult(
                    status=CalendarCreateStatus.COMMITTED, event=existing
                )
            return CalendarCreateResult(
                status=CalendarCreateStatus.AMBIGUOUS,
                error_code="precondition_failed_unresolved",
            )

        if response.status_code == 403:
            # Duplicate UID under a different resource name. Under normal
            # operation this cannot happen (both are derived deterministically
            # from the same operation_id); Ada cannot safely resolve it
            # without a UID-based search, which is out of MVP scope.
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
            existing = self._reconcile_via_marker(
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
