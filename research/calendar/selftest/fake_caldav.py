"""Minimal HTTPS CalDAV fake for the probe self-test (localhost only).

Generic behavior, not the IONOS profile: create-only PUT, If-Match checks,
409 for an overwrite without If-Match, conditional DELETE, REPORT returning
every stored event. Debug endpoints count stored events, credential leaks and
requests. Optional: DROP_FIRST_CREATE=1 commits the first create and closes
the connection without a response (lost response).

Usage: python3 fake_caldav.py PORT CERT KEY
"""

from __future__ import annotations

import hashlib
import os
import re
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EVENTS: dict[str, bytes] = {}
STATE = {
    "drop": os.environ.get("DROP_FIRST_CREATE") == "1",
    "leaks": 0,
    "requests": 0,
}


def etag(body: bytes) -> str:
    return '"' + hashlib.sha1(body).hexdigest()[:12] + '"'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _send(self, code: int, data: bytes = b"", ctype: str = "text/plain",
              extra: dict[str, str] | None = None) -> None:
        self.send_response(code)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _count(self) -> None:
        if not self.path.startswith("/debug/"):
            STATE["requests"] += 1

    def do_PROPFIND(self) -> None:
        self._count()
        self._body()
        xml = (
            b'<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" '
            b'xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:cs="http://calendarserver.org/ns/">'
            b"<d:response><d:href>/caldav/probe/</d:href><d:propstat><d:prop>"
            b"<d:resourcetype><d:collection/><c:calendar/></d:resourcetype>"
            b"<d:current-user-privilege-set><d:privilege><d:all/></d:privilege>"
            b"</d:current-user-privilege-set><c:supported-calendar-component-set>"
            b'<c:comp name="VEVENT"/></c:supported-calendar-component-set>'
            b"<cs:getctag>1</cs:getctag></d:prop></d:propstat></d:response>"
            b"</d:multistatus>"
        )
        self._send(207, xml, "application/xml")

    def do_PUT(self) -> None:
        self._count()
        body = self._body()
        current = EVENTS.get(self.path)
        if self.headers.get("If-None-Match") == "*":
            if current is not None:
                return self._send(412)
            uid = re.search(rb"UID:(\S+)", body)
            if uid and any(
                re.search(rb"UID:" + re.escape(uid.group(1)) + rb"\r", v)
                for v in EVENTS.values()
            ):
                return self._send(409)
            EVENTS[self.path] = body
            if STATE["drop"]:
                STATE["drop"] = False
                self.close_connection = True
                return
            return self._send(201, extra={"ETag": etag(body)})
        if current is None:
            return self._send(404)
        if_match = self.headers.get("If-Match")
        if if_match is None:
            return self._send(409)
        if if_match != etag(current):
            return self._send(412)
        EVENTS[self.path] = body
        return self._send(204, extra={"ETag": etag(body)})

    def do_GET(self) -> None:
        if self.path == "/debug/count":
            return self._send(200, str(len(EVENTS)).encode())
        if self.path == "/debug/leaks":
            return self._send(200, str(STATE["leaks"]).encode())
        if self.path == "/debug/requests":
            return self._send(200, str(STATE["requests"]).encode())
        if self.path.startswith("/debug/leak"):
            if self.headers.get("Authorization"):
                STATE["leaks"] += 1
            return self._send(200, b"leak")
        self._count()
        current = EVENTS.get(self.path)
        if current is None:
            return self._send(404)
        self._send(200, current, "text/calendar",
                   {"ETag": etag(current), "Date": self.date_time_string()})

    def do_DELETE(self) -> None:
        self._count()
        current = EVENTS.get(self.path)
        if current is None:
            return self._send(404)
        if_match = self.headers.get("If-Match")
        if if_match is not None and if_match != etag(current):
            return self._send(412)
        del EVENTS[self.path]
        self._send(204)

    def do_REPORT(self) -> None:
        self._count()
        self._body()
        parts = "".join(
            f"<d:response><d:href>{path}</d:href><d:propstat><d:prop>"
            f"<d:getetag>{etag(body).replace(chr(34), '&quot;')}</d:getetag>"
            f"<c:calendar-data>{body.decode().replace(chr(13), '&#13;')}</c:calendar-data>"
            f"</d:prop></d:propstat></d:response>"
            for path, body in EVENTS.items()
            if path.startswith(self.path)
        )
        xml = (
            '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" '
            f'xmlns:c="urn:ietf:params:xml:ns:caldav">{parts}</d:multistatus>'
        )
        self._send(207, xml.encode(), "application/xml")


def main() -> None:
    port, cert, key = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
