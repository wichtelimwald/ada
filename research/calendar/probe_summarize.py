"""Summarize CalDAV probe responses without printing personal data.

Research helper for ``ionos_caldav_probe.zsh`` (MVP-60). Standard library
only. It prints structural facts (privileges, supported components, presence
of change tokens) and synthetic probe fields. Any value that does not carry the
synthetic ``Ada probe`` / ``Probe place`` marker is redacted.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

DAV = "{DAV:}"
CALDAV = "{urn:ietf:params:xml:ns:caldav}"
CS = "{http://calendarserver.org/ns/}"

SUMMARY_MARKER = "Ada probe"
LOCATION_MARKER = "Probe place"
ANONYMIZED_SUMMARIES = {"Private", "Privat"}


def _parse(path: str) -> ET.Element:
    with open(path, "rb") as handle:
        data = handle.read()
    if b"<!DOCTYPE" in data.upper():
        raise SystemExit(f"{path}: refusing XML with a DOCTYPE declaration")
    return ET.fromstring(data)


def _norm_path(url_or_path: str) -> str:
    return unquote(urlsplit(url_or_path).path).rstrip("/") + "/"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def listing(xml_path: str, labelled_urls: list[str]) -> None:
    root = _parse(xml_path)
    labels = {}
    for item in labelled_urls:
        label, _, url = item.partition("=")
        labels[_norm_path(url)] = label

    calendars = []
    for response in root.iter(f"{DAV}response"):
        href = response.findtext(f"{DAV}href") or ""
        resourcetype = response.find(f".//{DAV}resourcetype")
        if resourcetype is None or resourcetype.find(f"{CALDAV}calendar") is None:
            continue
        privileges = sorted(
            {
                _local(child.tag)
                for privilege in response.iter(f"{DAV}privilege")
                for child in privilege
            }
        )
        components = sorted(
            comp.get("name", "?")
            for comp in response.iter(f"{CALDAV}comp")
        )
        has_ctag = any(
            (elem.text or "").strip() for elem in response.iter(f"{CS}getctag")
        )
        has_sync = any(
            (elem.text or "").strip() for elem in response.iter(f"{DAV}sync-token")
        )
        calendars.append((_norm_path(href), privileges, components, has_ctag, has_sync))

    print(f"P1 calendar collections visible to the Ada account: {len(calendars)}")
    matched = set()
    other_index = 0
    for norm, privileges, components, has_ctag, has_sync in calendars:
        label = labels.get(norm)
        if label is None:
            other_index += 1
            label = f"other#{other_index}"
        else:
            matched.add(norm)
        print(
            f"P1 {label}: privileges={','.join(privileges) or '-'} "
            f"components={','.join(components) or '-'} "
            f"ctag={'yes' if has_ctag else 'no'} sync-token={'yes' if has_sync else 'no'}"
        )
    for norm, label in labels.items():
        if norm not in matched:
            print(f"P1 {label}: NOT LISTED under the given URL path")


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _events(xml_path: str) -> list[dict[str, str]]:
    root = _parse(xml_path)
    events: list[dict[str, str]] = []
    for data in root.iter(f"{CALDAV}calendar-data"):
        current: dict[str, str] | None = None
        for line in _unfold(data.text or ""):
            if line == "BEGIN:VEVENT":
                current = {}
            elif line == "END:VEVENT" and current is not None:
                events.append(current)
                current = None
            elif current is not None and ":" in line:
                name_part, _, value = line.partition(":")
                name = name_part.split(";", 1)[0].upper()
                current.setdefault(name, value)
    return events


def events(xml_path: str, label: str) -> None:
    found = _events(xml_path)
    print(f"{label} VEVENT components returned: {len(found)}")
    for index, event in enumerate(found, start=1):
        summary = event.get("SUMMARY")
        if summary is None:
            shown_summary = "absent"
        elif summary.startswith(SUMMARY_MARKER) or summary in ANONYMIZED_SUMMARIES:
            shown_summary = repr(summary)
        else:
            shown_summary = "<redacted non-probe value>"
        location = event.get("LOCATION")
        if location is None:
            shown_location = "absent"
        elif location.startswith(LOCATION_MARKER):
            shown_location = repr(location)
        else:
            shown_location = "<redacted non-probe value>"
        print(
            f"{label} event#{index}: summary={shown_summary} "
            f"class={event.get('CLASS', 'absent')} location={shown_location} "
            f"transp={event.get('TRANSP', 'absent')} "
            f"rrule={'yes' if 'RRULE' in event else 'no'}"
        )


def count_uid(xml_path: str, uid: str) -> None:
    print(sum(1 for event in _events(xml_path) if event.get("UID") == uid))


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        raise SystemExit("usage: probe_summarize.py listing|events|count-uid FILE ARGS...")
    mode, xml_path, *rest = argv[1:]
    if mode == "listing":
        listing(xml_path, rest)
    elif mode == "events":
        events(xml_path, rest[0] if rest else "events")
    elif mode == "count-uid":
        count_uid(xml_path, rest[0])
    else:
        raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main(sys.argv)
