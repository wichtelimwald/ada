from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import xml.sax.saxutils as saxutils

import icalendar
import httpx2


def _xml_escape(value: str) -> str:
    return saxutils.escape(value)


class _ChunkedByteStream(httpx2.SyncByteStream):
    """Yields a known body in small chunks, without a ``Content-Length``
    header, so a caller can be proven to genuinely stream an ordinary
    (non-oversized) response end to end rather than only exercising the
    already-materialized ``content=`` mock shortcut.
    """

    def __init__(self, body: bytes, *, chunk_size: int = 16) -> None:
        self._body = body
        self._chunk_size = chunk_size
        self.closed = False

    def __iter__(self):
        for start in range(0, len(self._body), self._chunk_size):
            yield self._body[start : start + self._chunk_size]

    def close(self) -> None:
        self.closed = True


class _RaisingByteStream(httpx2.SyncByteStream):
    """Yields nothing and raises while being iterated.

    Simulates a body-read failure (for example a timeout) that happens
    *after* the response headers/status were already received and returned
    by ``client.send(..., stream=True)`` -- distinct from a failure during
    ``client.send()`` itself, which the existing fault injectors (a raised
    exception from the transport callable) already cover.
    """

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.closed = False

    def __iter__(self):
        raise self._exc
        yield b""  # pragma: no cover - makes this a generator function

    def close(self) -> None:
        self.closed = True


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
    etag: str = ""


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
        self.stream_normal_responses = False
        self.report_body_read_failure: Exception | None = None
        self.put_response_body_read_failure: Exception | None = None
        self.report_malformed_content_encoding = False
        self.get_malformed_content_encoding = False
        # Lose the response of the next N conditional writes (PUT with
        # If-Match, DELETE) *after* the provider committed them.
        self.lose_write_response_after_commit = 0
        # Lose the next N conditional writes *before* they are applied.
        self.lose_write_before_commit = 0
        # Answer the next conditional write with this status without applying
        # it (for example 503).
        self.conditional_write_status: int | None = None
        # Called once at the start of the next conditional write, before it is
        # evaluated: lets a test make a human edit between Ada's pre-read and
        # its write.
        self.before_next_conditional_write = None

        # Observability for assertions.
        self.received_time_ranges: list[tuple[datetime, datetime]] = []
        self.put_attempts = 0
        self.conditional_writes: list[tuple[str, str | None]] = []

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
        collection.resources[resource_path] = _StoredResource(
            body=ical_body, uid=uid, etag=self._new_etag()
        )

    def human_edit(
        self, configured_path: str, resource_name: str, ical_body: bytes
    ) -> str:
        """Simulate a webmail edit: replaces the body and changes the ETag."""

        collection = self._collections[configured_path]
        resource_path = f"{collection.canonical_href.rstrip('/')}/{resource_name}"
        stored = collection.resources[resource_path]
        stored.body = ical_body
        stored.etag = self._new_etag()
        return stored.etag

    def resource_body(self, configured_path: str, resource_name: str) -> bytes | None:
        collection = self._collections[configured_path]
        resource_path = f"{collection.canonical_href.rstrip('/')}/{resource_name}"
        stored = collection.resources.get(resource_path)
        return stored.body if stored else None

    def resource_etag(self, configured_path: str, resource_name: str) -> str | None:
        collection = self._collections[configured_path]
        resource_path = f"{collection.canonical_href.rstrip('/')}/{resource_name}"
        stored = collection.resources.get(resource_path)
        return stored.etag if stored else None

    def _new_etag(self) -> str:
        value = f"e{self._next_etag_id}"
        self._next_etag_id += 1
        return value

    def _multistatus_response(self, body: bytes) -> httpx2.Response:
        if self.stream_normal_responses:
            return httpx2.Response(
                207,
                headers={"Content-Type": "application/xml"},
                stream=_ChunkedByteStream(body),
            )
        return httpx2.Response(
            207, content=body, headers={"Content-Type": "application/xml"}
        )

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
        if method == "DELETE":
            return self._delete(path, request)
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
        return self._multistatus_response(body)

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

        if self.report_body_read_failure is not None:
            # Headers/status are genuinely returned; only the body fails
            # while being streamed, proving a post-send body-read failure is
            # classified rather than leaked raw (dav_client._consume_capped).
            return httpx2.Response(
                207,
                headers={"Content-Type": "application/xml"},
                stream=_RaisingByteStream(self.report_body_read_failure),
            )

        if self.report_malformed_content_encoding:
            # A declared Content-Encoding that the body does not actually
            # match: httpx2 raises httpx2.DecodingError while decoding
            # during iter_bytes(), distinct from a timeout/transport failure.
            # Must be a genuinely streamed response (like
            # report_body_read_failure above) -- httpx2.Response(content=...)
            # decodes eagerly inside __init__, which would raise here in the
            # fake server itself instead of later in the real client-side
            # iter_bytes() call this is meant to exercise.
            return httpx2.Response(
                207,
                headers={
                    "Content-Type": "application/xml",
                    "Content-Encoding": "gzip",
                },
                stream=_ChunkedByteStream(b"not actually gzip-encoded content"),
            )

        entries = []
        # Matches the observed OX/IONOS behavior: comp-filter/time-range are
        # not enforced server-side, so every stored resource is returned and
        # Ada's own client-side filtering must do the real work.
        for resource_path, resource in collection.resources.items():
            etag = resource.etag  # unquoted on purpose (probe P4j)
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
        return self._multistatus_response(body)

    def _get(self, path: str) -> httpx2.Response:
        for collection in self._collections.values():
            resource = collection.resources.get(path)
            if resource is not None:
                if self.get_malformed_content_encoding:
                    # See report_malformed_content_encoding above: must be a
                    # genuinely streamed response, not content=, or httpx2
                    # decodes eagerly in the fake server's own __init__.
                    return httpx2.Response(
                        200,
                        headers={
                            "Content-Type": "text/calendar",
                            "Content-Encoding": "gzip",
                        },
                        stream=_ChunkedByteStream(
                            b"not actually gzip-encoded content"
                        ),
                    )
                return httpx2.Response(
                    200,
                    content=resource.body,
                    headers={
                        "Content-Type": "text/calendar",
                        "ETag": f'"{resource.etag}"',
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
        vevent = next(iter(calendar.walk("VEVENT")))
        uid = str(vevent.get("uid"))
        for other_path, other in collection.resources.items():
            if other_path != path and other.uid == uid:
                return httpx2.Response(403, content=b"duplicate UID")

        if_match = request.headers.get("if-match")
        if if_match is not None:
            self.conditional_writes.append(("PUT", if_match))
            early = self._conditional_write_faults()
            if early is not None:
                return early
            existing = collection.resources.get(path)
            if existing is None:
                return httpx2.Response(404, content=b"not found")
            if if_match.strip() != f'"{existing.etag}"':
                return httpx2.Response(412, content=b"precondition failed")
            # Observed IONOS/OX rule: a lower SEQUENCE than the stored one is
            # refused.
            stored_vevent = next(
                iter(icalendar.Calendar.from_ical(existing.body).walk("VEVENT"))
            )
            if int(vevent.get("sequence", 0)) < int(stored_vevent.get("sequence", 0)):
                return httpx2.Response(412, content=b"sequence too low")
        # No If-Match: a blind overwrite is accepted (probe: not refused).

        stored = _StoredResource(body=request.content, uid=uid, etag=self._new_etag())
        collection.resources[path] = stored
        if if_match is not None and self.lose_write_response_after_commit > 0:
            self.lose_write_response_after_commit -= 1
            raise httpx2.ReadTimeout("simulated lost response after commit")
        if self.put_response_body_read_failure is not None:
            # The write already committed (the resource is stored above);
            # only the unused response body fails while being streamed, to
            # prove a create's outcome cannot depend on reading a write
            # response body no caller needs.
            return httpx2.Response(
                201,
                headers={"Content-Type": "text/calendar"},
                stream=_RaisingByteStream(self.put_response_body_read_failure),
            )
        # IONOS reports no ETag in the create response (probe P2); the
        # adapter must GET afterward to learn the version.
        return httpx2.Response(201, content=b"")

    def _conditional_write_faults(self) -> httpx2.Response | None:
        hook = self.before_next_conditional_write
        if hook is not None:
            self.before_next_conditional_write = None
            hook()
        if self.lose_write_before_commit > 0:
            self.lose_write_before_commit -= 1
            raise httpx2.ReadTimeout("simulated lost request before commit")
        if self.conditional_write_status is not None:
            status = self.conditional_write_status
            self.conditional_write_status = None
            return httpx2.Response(status, content=b"injected")
        return None

    def _delete(self, path: str, request: httpx2.Request) -> httpx2.Response:
        collection = self._collection_for_href(path.rsplit("/", 1)[0] + "/")
        if collection is None:
            return httpx2.Response(404, content=b"no such collection")

        if_match = request.headers.get("if-match")
        self.conditional_writes.append(("DELETE", if_match))
        early = self._conditional_write_faults()
        if early is not None:
            return early
        existing = collection.resources.get(path)
        if existing is None:
            return httpx2.Response(404, content=b"not found")
        if if_match is not None and if_match.strip() != f'"{existing.etag}"':
            return httpx2.Response(412, content=b"precondition failed")

        del collection.resources[path]
        if self.lose_write_response_after_commit > 0:
            self.lose_write_response_after_commit -= 1
            raise httpx2.ReadTimeout("simulated lost response after commit")
        return httpx2.Response(204, content=b"")
