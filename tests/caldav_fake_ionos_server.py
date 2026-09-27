from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import xml.sax.saxutils as saxutils

import icalendar
import httpx2


def _xml_escape(value: str) -> str:
    return saxutils.escape(value)


class _UnboundedByteStream(httpx2.SyncByteStream):
    """Yields many chunks, without any ``Content-Length`` header.

    Used to prove the response-size cap is enforced while *reading* a
    genuinely incremental response, not only after an already-materialized
    mock body has been checked post hoc. Bounded at a large but finite chunk
    count (rather than truly infinite) so a regression in the cap logic
    fails the test instead of hanging it forever.
    """

    def __init__(self, chunk: bytes, *, max_chunks: int = 1_000_000) -> None:
        self._chunk = chunk
        self._max_chunks = max_chunks
        self.chunks_yielded = 0
        self.closed = False

    def __iter__(self):
        for _ in range(self._max_chunks):
            self.chunks_yielded += 1
            yield self._chunk

    def close(self) -> None:
        self.closed = True


@dataclass
class _StoredResource:
    body: bytes
    uid: str


@dataclass
class _Collection:
    canonical_href: str
    privileges: frozenset[str]
    ctag: str
    resources: dict[str, _StoredResource] = field(default_factory=dict)


_TIME_RANGE_RE = re.compile(
    rb'<C:time-range start="([^"]+)" end="([^"]+)"'
)


def _parse_caldav_time(value: bytes) -> datetime:
    return datetime.strptime(value.decode("ascii"), "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )


class FakeIonosCalDAVServer:
    """In-process fake reproducing the recorded IONOS behavior.

    Evidence: [calendar provider evaluation](../docs/research/calendar-provider-evaluation.md)
    section 10 (maintainer probe runs 1-4, 2026-09-26). This fake deliberately
    ignores the REPORT time-range/comp-filter (matching the observed "silently
    ignored" OX behavior) so tests exercise Ada's own client-side window
    clamping and post-filtering rather than trusting the server.
    """

    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}
        self._next_etag_id = 1

        # Test-controlled fault injection, checked once per call.
        self.inject_doctype = False
        self.oversized_body: bytes | None = None
        self.stream_oversized_without_content_length = False
        self.last_unbounded_stream: _UnboundedByteStream | None = None
        self.wrong_origin_href: str | None = None
        self.force_redirect_methods: frozenset[str] = frozenset()

        # Observability for assertions.
        self.received_time_ranges: list[tuple[datetime, datetime]] = []
        self.put_attempts = 0

    def add_collection(
        self,
        configured_path: str,
        *,
        canonical_href: str | None = None,
        privileges: frozenset[str] = frozenset({"read", "write"}),
        ctag: str = "ctag-1",
    ) -> None:
        self._collections[configured_path] = _Collection(
            canonical_href=canonical_href or configured_path,
            privileges=privileges,
            ctag=ctag,
        )

    def seed_resource(
        self, configured_path: str, resource_name: str, ical_body: bytes
    ) -> None:
        collection = self._collections[configured_path]
        calendar = icalendar.Calendar.from_ical(ical_body)
        uid = str(next(iter(calendar.walk("VEVENT"))).get("uid"))
        resource_path = f"{collection.canonical_href.rstrip('/')}/{resource_name}"
        collection.resources[resource_path] = _StoredResource(body=ical_body, uid=uid)

    def _new_etag(self) -> str:
        value = f"e{self._next_etag_id}"
        self._next_etag_id += 1
        return value

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if self.inject_doctype:
            body = (
                b'<?xml version="1.0"?>'
                b'<!DOCTYPE D:multistatus [<!ENTITY x "y">]>'
                b'<D:multistatus xmlns:D="DAV:"/>'
            )
            return httpx2.Response(
                207, content=body, headers={"Content-Type": "application/xml"}
            )

        if self.oversized_body is not None:
            return httpx2.Response(
                207,
                content=self.oversized_body,
                headers={
                    "Content-Type": "application/xml",
                    "Content-Length": str(len(self.oversized_body)),
                },
            )

        if self.stream_oversized_without_content_length:
            self.last_unbounded_stream = _UnboundedByteStream(b"x" * 4096)
            return httpx2.Response(
                207,
                headers={"Content-Type": "application/xml"},
                stream=self.last_unbounded_stream,
            )

        path = request.url.path
        method = request.method

        if method in self.force_redirect_methods:
            return httpx2.Response(
                302, headers={"Location": "https://dav.mailbusiness.ionos.test/elsewhere"}
            )

        if method == "PROPFIND":
            return self._propfind(path)
        if method == "REPORT":
            return self._report(path, request.content)
        if method == "GET":
            return self._get(path)
        if method == "PUT":
            return self._put(path, request)
        return httpx2.Response(501, content=b"unsupported method in fake server")

    def _propfind(self, path: str) -> httpx2.Response:
        collection = self._collections.get(path)
        if collection is None:
            return httpx2.Response(404, content=b"no such collection")

        href = self.wrong_origin_href or collection.canonical_href
        privilege_xml = "".join(
            f"<D:privilege><D:{name}/></D:privilege>" for name in collection.privileges
        )
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:multistatus xmlns:D="DAV:" xmlns:CS="http://calendarserver.org/ns/">'
            "<D:response>"
            f"<D:href>{_xml_escape(href)}</D:href>"
            "<D:propstat><D:prop>"
            "<D:resourcetype><D:collection/></D:resourcetype>"
            f"<D:current-user-privilege-set>{privilege_xml}</D:current-user-privilege-set>"
            f"<CS:getctag>{_xml_escape(collection.ctag)}</CS:getctag>"
            "</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat>"
            "</D:response>"
            "</D:multistatus>"
        ).encode("utf-8")
        return httpx2.Response(
            207, content=body, headers={"Content-Type": "application/xml"}
        )

    def _collection_for_href(self, href_path: str) -> _Collection | None:
        for collection in self._collections.values():
            if collection.canonical_href == href_path:
                return collection
        return None

    def _report(self, path: str, request_body: bytes) -> httpx2.Response:
        collection = self._collection_for_href(path)
        if collection is None:
            return httpx2.Response(404, content=b"no such collection")

        match = _TIME_RANGE_RE.search(request_body)
        if match:
            self.received_time_ranges.append(
                (_parse_caldav_time(match.group(1)), _parse_caldav_time(match.group(2)))
            )

        entries = []
        # Matches the observed OX/IONOS behavior: comp-filter/time-range are
        # not enforced server-side, so every stored resource is returned and
        # Ada's own client-side filtering must do the real work.
        for resource_path, resource in collection.resources.items():
            etag = self._new_etag()  # unquoted on purpose (probe P4j)
            entries.append(
                "<D:response>"
                f"<D:href>{_xml_escape(resource_path)}</D:href>"
                "<D:propstat><D:prop>"
                f"<D:getetag>{etag}</D:getetag>"
                f"<C:calendar-data>{_xml_escape(resource.body.decode('utf-8'))}</C:calendar-data>"
                "</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat>"
                "</D:response>"
            )

        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            + "".join(entries)
            + "</D:multistatus>"
        ).encode("utf-8")
        return httpx2.Response(
            207, content=body, headers={"Content-Type": "application/xml"}
        )

    def _get(self, path: str) -> httpx2.Response:
        for collection in self._collections.values():
            resource = collection.resources.get(path)
            if resource is not None:
                return httpx2.Response(
                    200,
                    content=resource.body,
                    headers={
                        "Content-Type": "text/calendar",
                        "ETag": f'"{self._new_etag()}"',
                    },
                )
        return httpx2.Response(404, content=b"not found")

    def _put(self, path: str, request: httpx2.Request) -> httpx2.Response:
        self.put_attempts += 1
        collection = self._collection_for_href(
            path.rsplit("/", 1)[0] + "/"
        )
        if collection is None:
            return httpx2.Response(404, content=b"no such collection")

        if request.headers.get("if-none-match") == "*" and path in collection.resources:
            return httpx2.Response(412, content=b"precondition failed")

        calendar = icalendar.Calendar.from_ical(request.content)
        uid = str(next(iter(calendar.walk("VEVENT"))).get("uid"))
        for other_path, other in collection.resources.items():
            if other_path != path and other.uid == uid:
                return httpx2.Response(403, content=b"duplicate UID")

        collection.resources[path] = _StoredResource(body=request.content, uid=uid)
        # IONOS reports no ETag in the create response (probe P2); the
        # adapter must GET afterward to learn the version.
        return httpx2.Response(201, content=b"")
