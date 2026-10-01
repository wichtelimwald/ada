from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import httpx2

NS_DAV = "DAV:"
NS_CALDAV = "urn:ietf:params:xml:ns:caldav"
NS_CS = "http://calendarserver.org/ns/"


class CalDAVConfigurationError(ValueError):
    """The configured CalDAV origin/collection is invalid."""


class CalDAVNotAttemptedError(RuntimeError):
    """The request was never sent (connection/DNS/TLS failure, or a redirect)."""


class CalDAVAmbiguousTransportError(RuntimeError):
    """The request may have reached the server; its outcome is unknown."""


class CalDAVProtocolError(RuntimeError):
    """The server's response did not conform to the expected CalDAV shape."""


class CalDAVResponseTooLargeError(RuntimeError):
    """The response exceeded the configured size cap for this provider."""


class CalDAVUnsafeXmlError(RuntimeError):
    """The response contained a DOCTYPE declaration and was rejected unread."""


def _tag(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def validate_https_origin(base_url: str) -> tuple[str, str]:
    """Return (scheme, netloc) for a configured HTTPS-only provider origin."""

    parsed = urlsplit(base_url)
    if parsed.scheme != "https":
        raise CalDAVConfigurationError("CalDAV base_url must use https")
    if not parsed.netloc:
        raise CalDAVConfigurationError("CalDAV base_url must include a host")
    return parsed.scheme, parsed.netloc


def resolve_same_origin_href(base_url: str, href: str) -> str:
    """Join a server-reported href, rejecting any escape from the configured origin.

    A malicious or misconfigured server must not be able to redirect Ada's
    authenticated requests to another origin merely by echoing an absolute
    href in a WebDAV response (ADR-0009 section 5/7: only the configured
    provider origin).
    """

    scheme, netloc = validate_https_origin(base_url)
    parsed_href = urlsplit(href)

    if parsed_href.scheme or parsed_href.netloc:
        if parsed_href.scheme != scheme or parsed_href.netloc != netloc:
            raise CalDAVProtocolError(
                f"server href {href!r} escapes the configured origin"
            )
        return href

    return urljoin(base_url, href)


def build_client(
    *,
    base_url: str,
    auth: tuple[str, str],
    timeout_seconds: float = 15.0,
    transport: httpx2.BaseTransport | None = None,
) -> httpx2.Client:
    """Construct the hardened, proxy-independent CalDAV transport.

    ``trust_env=False`` ignores ambient proxy/certificate environment
    variables (same rationale as the reviewed local-Ollama transport).
    Redirects are never followed; a 3xx response is surfaced to the caller
    as an explicit protocol condition rather than silently chased.
    """

    validate_https_origin(base_url)
    return httpx2.Client(
        base_url=base_url,
        auth=auth,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx2.Timeout(timeout_seconds),
        transport=transport,
    )


_SAFE_METHODS = frozenset({"GET", "PROPFIND", "REPORT"})


@dataclass(frozen=True, slots=True)
class DavResponse:
    """One fully (but boundedly) read CalDAV response.

    Ada-owned wrapper around the transport's streamed response: the body has
    already been read once, incrementally, and capped while reading. Callers
    never touch ``httpx2``'s own streaming state and can read ``.content``
    any number of times without risking ``httpx2.ResponseNotRead`` (which a
    genuinely streamed response raises if ``.content`` is accessed instead of
    ``.read()``/an exhausted ``.iter_bytes()``) or reading the network stream
    twice.
    """

    status_code: int
    headers: httpx2.Headers
    content: bytes


def send_request(
    client: httpx2.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
    max_response_bytes: int,
) -> DavResponse:
    """Send one request, classifying transport failures per ADR-0009 section 6.

    Connection failures before a request is sent are "not attempted";
    timeouts or transport errors after sending are ambiguous. The response
    body is read incrementally and capped while reading (never materialized
    fully first via ``httpx2``'s own buffering ``.content``/``.read()``
    shortcut), so an untrusted or misbehaving response cannot exhaust memory
    regardless of whether the caller inspects the body.

    A redirect is never followed. For a safe (read) method that is simply a
    protocol/configuration condition ("not attempted": nothing unsafe
    happened). For an unsafe (write) method the request has already reached
    the server and produced a response, so the outcome cannot be treated as
    not-attempted; it is ambiguous and must be reconciled, never silently
    retried.
    """

    try:
        request = client.build_request(method, url, headers=headers, content=content)
        response = client.send(request, stream=True)
    except httpx2.ConnectError as exc:
        raise CalDAVNotAttemptedError(str(exc)) from exc
    except httpx2.ConnectTimeout as exc:
        raise CalDAVNotAttemptedError(str(exc)) from exc
    except httpx2.TimeoutException as exc:
        raise CalDAVAmbiguousTransportError(str(exc)) from exc
    except httpx2.TransportError as exc:
        raise CalDAVAmbiguousTransportError(str(exc)) from exc

    is_safe = method in _SAFE_METHODS

    if response.status_code in (301, 302, 303, 307, 308):
        response.close()
        if is_safe:
            raise CalDAVNotAttemptedError(
                f"unexpected redirect response {response.status_code}"
            )
        raise CalDAVAmbiguousTransportError(
            f"unexpected redirect response {response.status_code} "
            "after a write request was already sent"
        )

    if not is_safe:
        # A write's response body is never used by any caller (the status
        # code is already the provider evidence, ADR-0009 section 6). Once
        # headers arrive that evidence is final; reading an unneeded body
        # must not be able to put it at risk of an unrelated body-read
        # failure (for example a timeout partway through an empty/short
        # body).
        result = DavResponse(
            status_code=response.status_code, headers=response.headers, content=b""
        )
        response.close()
        return result

    try:
        body = _consume_capped(response, max_bytes=max_response_bytes)
    except BaseException:
        response.close()
        raise

    result = DavResponse(
        status_code=response.status_code, headers=response.headers, content=body
    )
    response.close()
    return result


def _consume_capped(response: httpx2.Response, *, max_bytes: int) -> bytes:
    """Read a streamed response body, aborting as soon as it exceeds the cap.

    Reads incrementally via ``iter_bytes()`` rather than the buffering
    ``.content``/``.read()`` shortcut, so an oversized or falsely-labeled
    response is capped while reading, not after it is already fully in
    memory. The accepted (within-cap) chunks are retained and returned so a
    genuinely streamed response's body is not lost after being consumed.

    Only called for safe (read) requests -- see ``send_request`` -- whose
    caller actually needs the body. A timeout/transport error raised by
    ``iter_bytes()`` itself (the request was already sent and a response was
    already received; only the body did not finish) is classified the same
    way as any other post-send transport failure instead of leaking the raw
    ``httpx2`` exception through this module's typed boundary. ``iter_bytes()``
    also performs HTTP content decoding (gzip/deflate/brotli/zstd); malformed
    encoded content raises ``httpx2.DecodingError``, which -- unlike a
    timeout -- is a ``RequestError`` but not a ``TransportError`` in httpx2,
    so it needs its own translation to stay inside this module's typed
    boundary. It is a malformed-response condition, not a connectivity one,
    so it becomes ``CalDAVProtocolError`` rather than the ambiguous-transport
    error.
    """

    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            declared_bytes = int(declared)
        except ValueError:
            declared_bytes = None
        if declared_bytes is not None and declared_bytes > max_bytes:
            raise CalDAVResponseTooLargeError(
                f"response declared {declared_bytes} bytes, exceeds cap {max_bytes}"
            )

    total = 0
    chunks: list[bytes] = []
    try:
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise CalDAVResponseTooLargeError(
                    f"response body exceeds the {max_bytes}-byte cap"
                )
            chunks.append(chunk)
    except httpx2.DecodingError as exc:
        raise CalDAVProtocolError(
            f"response content could not be decoded: {exc}"
        ) from exc
    except (httpx2.TimeoutException, httpx2.TransportError) as exc:
        raise CalDAVAmbiguousTransportError(
            f"reading the response body failed: {exc}"
        ) from exc
    return b"".join(chunks)


def parse_safe_xml(content: bytes) -> ElementTree.Element:
    """Parse untrusted server XML, rejecting DOCTYPE declarations outright.

    CalDAV/WebDAV responses never legitimately need a DOCTYPE. Rejecting it
    unconditionally (ADR-0009 section 5) avoids entity-expansion and
    external-entity classes of attack without adding a parsing dependency.
    """

    if b"<!doctype" in content.lower():
        raise CalDAVUnsafeXmlError("XML response contains a rejected DOCTYPE")
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise CalDAVProtocolError(f"malformed XML response: {exc}") from exc


def normalize_etag(raw: str) -> str:
    """Normalize an entity tag to its quoted form (RFC 7232).

    IONOS reports the ``GET`` header quoted but the ``REPORT`` ``getetag``
    property unquoted (evaluation section 10, probe P4j); Ada must compare
    and send only the normalized quoted form.
    """

    value = raw.strip()
    prefix = ""
    if value.startswith("W/"):
        prefix = "W/"
        value = value[2:].strip()
    if not (value.startswith('"') and value.endswith('"') and len(value) >= 2):
        value = f'"{value}"'
    return prefix + value


def format_time_range_bound(value: datetime) -> str:
    """Render a datetime as the UTC basic-ISO form CalDAV time-range expects.

    ``strftime`` preserves the input wall clock; a non-UTC offset must be
    converted first or the sent bound silently shifts by that offset.
    """

    if value.tzinfo is None or value.utcoffset() is None:
        raise CalDAVConfigurationError(
            "time-range bound must be timezone-aware"
        )
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True, slots=True)
class CollectionInfo:
    """Result of a ``PROPFIND`` privilege/ctag check on one configured collection."""

    href: str
    privileges: frozenset[str]
    ctag: str | None


def propfind_collection(
    client: httpx2.Client,
    *,
    base_url: str,
    collection_path: str,
    max_response_bytes: int,
) -> CollectionInfo:
    """Depth-0 ``PROPFIND`` for privileges, ctag, and the canonical href.

    Ada configures collection URLs explicitly (no discovery, ADR-0009
    section 2); this call still adopts whatever href the server echoes back
    as the operative address for later requests (evaluation section 3:
    "the collection also has an opaque canonical URL besides the requested
    alias").

    ``collection_path`` is untrusted household configuration, not a
    server-reported value: it is validated against ``base_url`` *before*
    anything is sent, so a misconfigured or malicious absolute collection
    URL on another origin is rejected before the request (and its Basic
    Auth header) ever leaves the process.
    """

    resolved_path = resolve_same_origin_href(base_url, collection_path)

    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<D:propfind xmlns:D="DAV:" xmlns:CS="http://calendarserver.org/ns/">'
        "<D:prop>"
        "<D:resourcetype/>"
        "<D:current-user-privilege-set/>"
        "<CS:getctag/>"
        "</D:prop>"
        "</D:propfind>"
    ).encode("utf-8")

    response = send_request(
        client,
        "PROPFIND",
        resolved_path,
        headers={
            "Content-Type": 'application/xml; charset="utf-8"',
            "Depth": "0",
        },
        content=body,
        max_response_bytes=max_response_bytes,
    )
    if response.status_code != 207:
        raise CalDAVProtocolError(
            f"PROPFIND on {resolved_path!r} returned {response.status_code}"
        )

    root = parse_safe_xml(response.content)

    resp_elem = root.find(_tag(NS_DAV, "response"))
    if resp_elem is None:
        raise CalDAVProtocolError("PROPFIND multistatus has no response element")

    href_elem = resp_elem.find(_tag(NS_DAV, "href"))
    if href_elem is None or not (href_elem.text or "").strip():
        raise CalDAVProtocolError("PROPFIND response is missing a href")
    href = resolve_same_origin_href(base_url, href_elem.text.strip())

    privileges: set[str] = set()
    for privilege_elem in resp_elem.iter(_tag(NS_DAV, "privilege")):
        for child in privilege_elem:
            local = child.tag.rsplit("}", 1)[-1]
            privileges.add(local)

    ctag_elem = resp_elem.find(f".//{_tag(NS_CS, 'getctag')}")
    ctag = ctag_elem.text.strip() if ctag_elem is not None and ctag_elem.text else None

    return CollectionInfo(href=href, privileges=frozenset(privileges), ctag=ctag)


@dataclass(frozen=True, slots=True)
class CalendarQueryEntry:
    """One raw (unparsed) entry returned by a ``calendar-query`` REPORT."""

    href: str
    etag: str | None
    calendar_data: bytes


def calendar_query(
    client: httpx2.Client,
    *,
    base_url: str,
    collection_href: str,
    start: datetime,
    end: datetime,
    max_response_bytes: int,
) -> list[CalendarQueryEntry]:
    """Bounded ``REPORT calendar-query`` for VEVENT components in [start, end).

    ``comp-filter`` is not trusted to actually restrict the response
    (evaluation section 3: "comp-filter and is-not-defined filters are
    silently ignored" on OX); callers must still post-filter components.
    """

    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
        "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
        '<C:filter><C:comp-filter name="VCALENDAR">'
        '<C:comp-filter name="VEVENT">'
        f'<C:time-range start="{format_time_range_bound(start)}" '
        f'end="{format_time_range_bound(end)}"/>'
        "</C:comp-filter></C:comp-filter></C:filter>"
        "</C:calendar-query>"
    ).encode("utf-8")

    response = send_request(
        client,
        "REPORT",
        collection_href,
        headers={
            "Content-Type": 'application/xml; charset="utf-8"',
            "Depth": "1",
        },
        content=body,
        max_response_bytes=max_response_bytes,
    )
    if response.status_code != 207:
        raise CalDAVProtocolError(
            f"REPORT calendar-query on {collection_href!r} "
            f"returned {response.status_code}"
        )

    root = parse_safe_xml(response.content)

    entries: list[CalendarQueryEntry] = []
    for resp_elem in root.findall(_tag(NS_DAV, "response")):
        href_elem = resp_elem.find(_tag(NS_DAV, "href"))
        if href_elem is None or not (href_elem.text or "").strip():
            continue
        href = resolve_same_origin_href(base_url, href_elem.text.strip())

        data_elem = resp_elem.find(f".//{_tag(NS_CALDAV, 'calendar-data')}")
        if data_elem is None or not data_elem.text:
            continue

        etag_elem = resp_elem.find(f".//{_tag(NS_DAV, 'getetag')}")
        etag = (
            normalize_etag(etag_elem.text)
            if etag_elem is not None and etag_elem.text
            else None
        )

        entries.append(
            CalendarQueryEntry(
                href=href,
                etag=etag,
                calendar_data=data_elem.text.encode("utf-8"),
            )
        )

    return entries


@dataclass(frozen=True, slots=True)
class GetResourceResult:
    calendar_data: bytes
    etag: str | None


def get_resource(
    client: httpx2.Client,
    resource_href: str,
    *,
    max_response_bytes: int,
) -> GetResourceResult | None:
    """``GET`` one event resource; ``None`` when the provider reports 404."""

    response = send_request(
        client, "GET", resource_href, max_response_bytes=max_response_bytes
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise CalDAVProtocolError(
            f"GET {resource_href!r} returned {response.status_code}"
        )

    raw_etag = response.headers.get("etag")
    etag = normalize_etag(raw_etag) if raw_etag else None
    return GetResourceResult(calendar_data=response.content, etag=etag)


def put_create_only(
    client: httpx2.Client,
    resource_href: str,
    *,
    body: bytes,
    max_response_bytes: int,
) -> DavResponse:
    """Create-only ``PUT`` (``If-None-Match: *``); never overwrites a resource."""

    return send_request(
        client,
        "PUT",
        resource_href,
        headers={
            "If-None-Match": "*",
            "Content-Type": "text/calendar; charset=utf-8",
        },
        max_response_bytes=max_response_bytes,
        content=body,
    )


def put_conditional(
    client: httpx2.Client,
    resource_href: str,
    *,
    body: bytes,
    if_match: str,
    max_response_bytes: int,
) -> DavResponse:
    """Overwriting ``PUT`` that only succeeds against ``if_match`` (RFC 9110)."""

    return send_request(
        client,
        "PUT",
        resource_href,
        headers={
            "If-Match": if_match,
            "Content-Type": "text/calendar; charset=utf-8",
        },
        max_response_bytes=max_response_bytes,
        content=body,
    )


def delete_conditional(
    client: httpx2.Client,
    resource_href: str,
    *,
    if_match: str,
    max_response_bytes: int,
) -> DavResponse:
    """``DELETE`` that only succeeds against ``if_match`` (RFC 9110)."""

    return send_request(
        client,
        "DELETE",
        resource_href,
        headers={"If-Match": if_match},
        max_response_bytes=max_response_bytes,
    )
