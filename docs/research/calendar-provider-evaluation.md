# Technology evaluation — first real calendar provider (MVP-60)

**Status:** Research; decision proposed in [ADR-0009](../decisions/ADR-0009-calendar-provider-integration.md).
Provider-specific facts marked *probe* still need evidence from
[the IONOS probe](../../research/calendar/README.md).

- **Date checked:** 2026-09-26
- **Step plan:** [MVP-60](../plans/MVP-60-real-calendar-provider.md)

## 1. User need

Ada must maintain the family calendar through a real provider: read events,
create/update/cancel ordinary events, detect conflicts including approximate
travel time, and never claim or duplicate a real-world effect it cannot prove
(ADR-0005). Calendar facts stay source-owned (ADR-0008).

The maintainer selected **IONOS Mail Business** as the first provider
(2026-09-26) and asked that other providers remain addable later through the
modular adapter architecture.

## 2. Constraints

### Must have

- Ada-owned `CalendarPort` semantics; provider types never cross the adapter boundary.
- Duplicate-safe create and reconcilable update/cancel (ADR-0005).
- Least-privilege credentials; no family member's primary password in Ada.
- Private event details must not be required for busy-time use (ADR-0004 `calendar.disclose.busy` vs `.detail`).
- No implicit third-party egress: traffic only to the configured provider origin.
- Calendar content (titles, locations, descriptions) is untrusted data, never instructions.
- Tests without real personal event fixtures.
- Dependencies pass the license/distribution gate (NOTICE.md policy).

### Non-goals for this evaluation

- Choosing a second provider or a runtime plugin mechanism.
- Email (MVP-70), contacts, tasks (VTODO).
- Production secret management and packaging (MVP-90).

## 3. Provider facts: IONOS Mail Business

| Fact | Evidence | Confidence |
| --- | --- | --- |
| IONOS Mail Business is built on Open-Xchange (OX) App Suite. | [IONOS OX App Suite article](https://www.ionos.com/digitalguide/startup/productivity/ox-app-suite/), [third-party Thunderbird setup note](https://www.maffulli.net/2020/12/09/how-to-configure-thunderbird-to-work-with-ionos-business-email-open-xchange/) | High |
| Each calendar has an individual CalDAV URL, shown in webmail → Calendar → ⋯ → Properties; clients authenticate with the full mailbox address and password. | [IONOS: sync calendar with macOS](https://www.ionos.com/help/email/managing-mail-business/syncing-mail-business-calendar-with-mac-os-x/) | High |
| Mail Business supports two-step verification; app passwords are then required for clients. The documented dialog asks only for an app **name**. | [IONOS: 2FA and app passwords](https://www.ionos.com/help/email/using-webmail/email-activate-and-configure-two-step-verification/) | High for existence; scope *probe* (M1, P9) |
| OX App Suite itself supports **scoped** application passwords (CalDAV-only scopes `dav`, `read_caldav`, `write_caldav`). Whether IONOS exposes that choice is unknown. | [OX application passwords](https://documentation.open-xchange.com/appsuite/security/application_passwords.html), [OX 8.20 docs](https://documentation.open-xchange.com/8.20/middleware/login_and_sessions/application_passwords.html) | *probe* |
| OX publishes all calendar folders of a user via CalDAV; whether IONOS includes calendars **shared with** the user is not documented. | [OX CalDAV/CardDAV](https://documentation.open-xchange.com/latest/middleware/miscellaneous/caldav_carddav.html) | *probe* (P1, M3) |

### OX App Suite CalDAV behavior relevant to Ada

Sources: [OX calendar implementation details](https://documentation.open-xchange.com/7.10.1/middleware/components/calendar/implementation_details.html),
[OX calendar overview](https://documentation.open-xchange.com/8/middleware/calendar.html),
[OX CalDAV clients](https://documentation.open-xchange.com/8/middleware/miscellaneous/caldav_carddav/caldav_clients.html),
and the OX profile in python-caldav 3.3.1 `caldav/compatibility_hints.py`
(observed against a self-hosted OX Docker image, dated probes 2026-06 to
2026-09; not IONOS).

| Behavior | Consequence for Ada |
| --- | --- |
| `CONFIDENTIAL` events appear to non-attending viewers of a shared folder as anonymous blocks with summary "Private"; `PRIVATE` events are not exposed to them at all and do not count in free/busy. | Owners control disclosure at the source. Ada receives busy-only data for confidential events and nothing for private ones. Ada cannot detect conflicts with `PRIVATE` events it cannot see; this must be user-visible. |
| Updates require `If-Match`; a blind overwrite is rejected with 409. | Optimistic concurrency is enforced by the provider. Ada must always read-modify-write with ETags. |
| The object resource name is preserved; the collection also has an opaque canonical URL (`cal://0/NNN`, base64 path) besides the requested alias. | Ada addresses events by `<canonical collection URL>/<resource name>`, adopting the canonical URL reported by the server. |
| Server-side recurrence expansion is unsupported; time-range queries do find recurring events whose occurrences fall in range (within the window). | Ada must expand recurrences client-side. |
| Queries use a sliding window (OX defaults `com.openexchange.caldav.interval.start=one_month`, `...interval.end=one_year`); unbounded queries are broken. | Ada must query bounded ranges and report the provider window as a limit. IONOS values: *probe* (P8). |
| `comp-filter` and `is-not-defined` filters are silently ignored. | Ada post-filters components client-side. |
| RFC 4791 `free-busy-query` returns 400. | Busy-time must be derived from event reads, not a free/busy report. |
| Limited RRULE set (legacy subset of DAILY/WEEKLY/MONTHLY/YEARLY parts). Rescheduling a series with exceptions returns 409. | Writing recurring series is risky; MVP writes only non-recurring events. |
| Only the organizer may change group-scheduled events; attendee `PARTSTAT` cannot be changed via PUT (403). Conversion between OX's internal model and iCalendar is "lossy best effort". | Ada writes attendee-less events only. `X-` property preservation is *probe* (P3). Whether attendee-less writes trigger notifications is *probe* (M4). |

## 4. Access topology alternatives

| Option | Description | Assessment |
| --- | --- | --- |
| **A1 Ada-owned mailbox + provider-side sharing** | Ada gets its own IONOS mailbox. Family members share selected calendars with it as read-only or write. Ada uses an app password of **its own** mailbox. | **Recommended.** No family credentials in Ada; per-calendar rights are enforced and revocable by each owner; confidential/private semantics apply at the source; matches the discovery idea of a dedicated Ada identity and serves MVP-70. Requires P1/P6 confirmation. Residual risk: one Ada credential reads every calendar shared with Ada. |
| A2 Per-member app passwords | Ada stores an app password for each family member's mailbox. | Rejected: Ada would hold family members' credentials, likely with mailbox-wide scope (P9), and would see private events. |
| A3 macOS EventKit via Calendar.app | IONOS accounts configured in macOS; Ada reads/writes through EventKit. | Rejected for MVP: calendar permission covers every account in Calendar.app, requires a native host process (not container-compatible, ADR-0003), and hides provider outcome evidence behind macOS sync. |
| A4 ICS subscription URLs | Read-only secret feeds. | Not sufficient: no writes, bearer-URL secrets, polling latency. Possible later read-only source for external calendars. |

## 5. Protocol alternatives

- **CalDAV (RFC 4791)** — standard, documented by IONOS, portable to other providers (Nextcloud, Fastmail, mailbox.org, iCloud). **Selected direction.**
- **OX HTTP API** — proprietary JSON API; richer (sharing, free/busy), but no evidence that IONOS exposes it for third-party clients; provider lock-in.
- **Exchange ActiveSync / JMAP Calendars** — no IONOS evidence; not considered further.

## 6. Client library alternatives and license gate

Checked 2026-09-26 on PyPI and GitHub. Ada-owned code is MIT; NOTICE.md
requires an explicit decision before adopting copyleft or network-copyleft
components.

| Option | Version / date | Code license | Notable dependencies | Assessment |
| --- | --- | --- | --- | --- |
| python-caldav | 3.3.1 / 2026-09-16 | Apache-2.0 OR GPL-3.0-or-later | **`icalendar-searcher` (AGPL-3.0-or-later**, confirmed via GitHub license API), `recurring-ical-events` and `x-wr-timezone` (LGPL-3.0-or-later), `niquests` → `urllib3-future` → `qh3` (separate HTTP/QUIC stack), `lxml`, `dnspython`, `pyyaml` | **Rejected.** Hard AGPL transitive dependency; bypasses Ada's reviewed `httpx2` transport (proxy-independence); broad surface (scheduling, principal search, calendar creation) Ada does not need. Its OX compatibility notes remain valuable evidence. |
| python-caldav 2.1.x | 2.1.2 / 2025-11-08 | as above | no `icalendar-searcher`; still `niquests`, `lxml`, `recurring-ical-events` | Rejected: pins an outdated major line and still brings a second HTTP stack. |
| vdirsyncer | 0.21.0 / 2026-09-04 | not re-verified (GitHub reports NOASSERTION) | — | Rejected for writes: file-sync semantics lose direct per-operation outcome evidence required by ADR-0005. |
| **Thin Ada-owned CalDAV adapter** | — | MIT (Ada) | `httpx2` 2.13.1 (already adopted, BSD-3-Clause), stdlib XML, **`icalendar` 7.3.0** | **Recommended.** Ada needs a narrow subset: bounded `calendar-query` REPORT, `PROPFIND` for listing/privileges, `GET`/`PUT` with `If-None-Match`/`If-Match`, conditional `DELETE`. Ada owns the security-relevant transport and outcome semantics. |
| icalendar | 7.3.0 / 2026-08-19 | BSD-2-Clause (`LICENSE.rst`, Plone Foundation) | `python-dateutil` (Apache-2.0/BSD dual), `six` (MIT), `tzdata` (Apache-2.0) | **Recommended** for RFC 5545 parsing/serialization (folding, escaping, VTIMEZONE). Writing a custom iCalendar parser is rejected. |
| vobject | 0.9.9 / 2024-12-16 | Apache-2.0 | `pytz`, `six` | Alternative parser; less active; no advantage. |

### Recurrence expansion (decision needed)

OX does not expand recurrences server-side, so Ada must.

| Option | License | Assessment |
| --- | --- | --- |
| **R1 `recurring-ical-events` 3.8.2** (2026-04-30) | LGPL-3.0-or-later; pulls `x-wr-timezone` 2.0.1 (LGPL-3.0-or-later) and `click` (BSD-3-Clause) | Purpose-built and actively maintained (repository activity 2026-09); handles RRULE/RDATE/EXDATE/RECURRENCE-ID overrides and time zones. Pure Python, used unmodified as a separately installed package. Same obligation class as the existing `psycopg-binary` LGPL path (NOTICE.md). Needs an explicit copyleft adoption decision. |
| R2 Ada-owned expansion on `python-dateutil` `rrule` | Apache-2.0/BSD | No copyleft, but Ada would own override/exception/DST correctness — a classic source of silent calendar bugs. |
| R3 No expansion; treat any recurring series in range as "possible conflict" | — | Fails the conflict-detection DoD for ordinary weekly family events. |

Recommendation: R1, subject to the maintainer's copyleft decision; R2 only if
LGPL is unacceptable, with a dedicated recurrence test corpus.

## 7. Transport and parsing security

- `httpx2.Client(trust_env=False)`: no ambient proxy/certificate environment (same rationale as [the httpx2 review](httpx2-direct-transport-review.md)); TLS verification on; HTTPS only.
- Only the configured provider origin; no redirect following (collection URLs are configured, not discovered via `.well-known`).
- Explicit timeouts and a response-size cap; bounded time ranges.
- Server XML is untrusted: parse with the standard library, reject DOCTYPE declarations, never resolve entities.
- Event text (summary, location, description) is untrusted content: never instructions, minimal fields to the model, description not read into context by default.
- Distinguish "request not sent" (connection refused, DNS, TLS failure → not attempted) from "response lost" (timeout after send → ambiguous → reconcile).

## 8. Travel-time source alternatives

| Option | Egress | Assessment |
| --- | --- | --- |
| **T1 Configured approximate durations between registered places** | none | **Recommended for MVP.** Deterministic, local, visibly approximate; unknown pairs yield "travel time unknown" instead of zero. |
| T2 Self-hosted routing engine (OSRM, Valhalla, GraphHopper) on OpenStreetMap data | none after data download | Later candidate if T1 is too laborious. Engine licenses (OSRM BSD-2-Clause and GraphHopper Apache-2.0 per GitHub; Valhalla not re-verified) and **OSM data under ODbL** (attribution, share-alike for derived databases), plus memory/disk cost on the M1/16 GB target, need their own review. |
| T3 Cloud routing APIs | addresses to a third party | Not an MVP default; would require explicit, informed egress consent. |

## 9. Credential storage (MVP-60 scope only)

Production secret management belongs to MVP-90. MVP-60 needs a safe
development path for the Ada app password:

- **S1 macOS Keychain** via `/usr/bin/security` (no new dependency): encrypted at rest, not in environment/argv/logs; host-only.
- **S2 owner-only file** (`0600`, regular file, no symlink, outside repository and Memory root): portable to containers; plaintext on a FileVault-protected disk.
- Environment variables and command-line arguments are rejected (child-process inheritance, process listings, shell history).

## 10. Evidence still required

See [the probe](../../research/calendar/README.md): shared-calendar visibility
and enforcement (P1/P6/M3), create-only semantics (P2), identity/X-property
preservation (P3), conditional writes (P4/P7), classification visibility
(P5/M2), query window (P8), credential scope (P9/M1), and notification side
effects (M4).
