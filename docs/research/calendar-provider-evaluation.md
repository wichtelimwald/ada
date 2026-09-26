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
modular adapter architecture. The family gets one IONOS mailbox, for Ada, and
the maintainer chose the **Ada-owned calendar** access model (section 4).

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
| OX publishes all calendar folders of a user via CalDAV; whether IONOS includes calendars **shared with** the user is not documented. | [OX CalDAV/CardDAV](https://documentation.open-xchange.com/latest/middleware/miscellaneous/caldav_carddav.html) | *probe* (optional P5/P6) |
| The Mail Business CalDAV host is `dav.mailbusiness.ionos.de`; calendar URLs use OX's opaque form `/caldav/<base64 of cal://0/N>`. | Ada mailbox webmail, observed by the maintainer 2026-09-26 | High |
| OX can share calendar folders with external people as invited guests or through anonymous links; external calendar shares are documented as read-only, anonymous links can carry an expiry, and `?ical=true` returns iCalendar for subscriptions. Guests do not see other folders. Whether IONOS enables this for Mail Business is not documented. | [OX sharing and guest mode](https://documentation.open-xchange.com/7.10.5/middleware/miscellaneous/sharing_and_guest_mode.html) | *probe* (P10, M2, M3) |

### OX App Suite CalDAV behavior relevant to Ada

Sources: [OX calendar implementation details](https://documentation.open-xchange.com/7.10.1/middleware/components/calendar/implementation_details.html),
[OX calendar overview](https://documentation.open-xchange.com/8/middleware/calendar.html),
[OX CalDAV clients](https://documentation.open-xchange.com/8/middleware/miscellaneous/caldav_carddav/caldav_clients.html),
and the OX profile in python-caldav 3.3.1 `caldav/compatibility_hints.py`
(observed against a self-hosted OX Docker image, dated probes 2026-06 to
2026-09; not IONOS).

| Behavior | Consequence for Ada |
| --- | --- |
| `CONFIDENTIAL` events appear to non-attending viewers of a shared folder as anonymous blocks with summary "Private"; `PRIVATE` events are not exposed to them at all and do not count in free/busy. | Relevant only for inbound sharing (a later option): the owner would control disclosure at the source, and Ada could not see private events. In the Ada-owned model, Ada owns every event and AdaGuard enforces disclosure. |
| Self-hosted OX: updates require `If-Match`; a blind overwrite is rejected with 409. **IONOS (run 1): a blind overwrite is accepted (201)**; a stale `If-Match` is rejected (412). | The provider does not enforce optimistic concurrency on IONOS. Ada must always send `If-Match` itself; other clients can still overwrite blindly. |
| The object resource name is preserved; the collection also has an opaque canonical URL (`cal://0/NNN`, base64 path) besides the requested alias. | Ada addresses events by `<canonical collection URL>/<resource name>`, adopting the canonical URL reported by the server. |
| Server-side recurrence expansion is unsupported; time-range queries do find recurring events whose occurrences fall in range (within the window). | Ada must expand recurrences client-side. |
| Queries use a sliding window (OX defaults `com.openexchange.caldav.interval.start=one_month`, `...interval.end=one_year`); unbounded queries are broken. | Ada must query bounded ranges and report the provider window as a limit. IONOS run 1: events 18 months ahead and 3 months back are not returned by time-range queries; boundaries *probe* (run 2). |
| `comp-filter` and `is-not-defined` filters are silently ignored. | Ada post-filters components client-side. |
| RFC 4791 `free-busy-query` returns 400. | Busy-time must be derived from event reads, not a free/busy report. |
| Limited RRULE set (legacy subset of DAILY/WEEKLY/MONTHLY/YEARLY parts). Rescheduling a series with exceptions returns 409. | Writing recurring series is risky; MVP writes only non-recurring events. |
| Only the organizer may change group-scheduled events; attendee `PARTSTAT` cannot be changed via PUT (403). Conversion between OX's internal model and iCalendar is "lossy best effort". | Ada writes attendee-less events only. `X-` property preservation is *probe* (P3). Whether attendee-less writes trigger notifications is *probe* (M4). |

## 4. Access topology alternatives

| Option | Description | Assessment |
| --- | --- | --- |
| **A0 Ada-owned calendars shared outward** | Ada's single mailbox holds one calendar per family member plus one family calendar (created once in webmail). Ada is the owner and regular writer; family members subscribe to the calendars shared with them. | **Selected for the MVP by the maintainer (2026-09-26).** Needs only one mailbox; Ada keeps full control; single writer keeps concurrency simple; no family credentials. Trade-offs: all family calendars in one account; separation between members depends on share distribution and AdaGuard; share links are bearer secrets; subscriptions are read-only and refresh on the client's schedule; Ada cannot see appointments kept elsewhere. Requires P10/M2/M3 confirmation. |
| A1 Inbound sharing to Ada's mailbox | Family members with their own mailboxes in the same contract share selected calendars with Ada as read-only or write. | Later option. Owners keep control and source-side confidential/private semantics apply, but every member needs a paid mailbox. The probe keeps optional checks (P5, P6). |
| A2 Per-member app passwords | Ada stores an app password for each family member's mailbox. | Rejected: Ada would hold family members' credentials, likely with mailbox-wide scope (P9), and would see private events. |
| A3 macOS EventKit via Calendar.app | IONOS accounts configured in macOS; Ada reads/writes through EventKit. | Rejected for MVP: calendar permission covers every account in Calendar.app, requires a native host process (not container-compatible, ADR-0003), and hides provider outcome evidence behind macOS sync. |
| A4 Ada reads external ICS feeds | Read-only secret feeds of calendars kept elsewhere. | Not sufficient on its own: no writes, bearer-URL secrets, polling latency. Possible later read-only source for appointments kept outside Ada's calendars. |

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

### Is python-caldav the only option?

For Python, effectively yes: it is the only maintained, full-featured CalDAV
client found (PyPI/GitHub search 2026-09-26).

| Other candidate | License / state | Fit |
| --- | --- | --- |
| aiocaldav 0.5.1 | GPL, last release 2018 | Unmaintained. |
| webdav4 0.11.0 | MIT, active | Generic WebDAV file access; no CalDAV `REPORT`/iCalendar semantics. |
| go-webdav (Go), tsdav (TypeScript), libdav 0.11.0 (Rust) | MIT, MIT, ISC; active | Would need a sidecar process in another language: a second runtime, build chain and IPC boundary for a small protocol subset. |
| Upstream change | — | Asking python-caldav/icalendar-searcher to make the AGPL dependency optional or relicense it is possible, but its outcome and timing are outside Ada's control. Re-open trigger in ADR-0009. |

### Size of the Ada-owned subset (estimate)

The hard parts are delegated: `icalendar` parses/serializes RFC 5545 and
`recurring-ical-events` expands recurrences. Ada writes the HTTP/XML glue:

| Part | Estimated production lines |
| --- | ---: |
| Transport setup, origin/redirect/size limits, error mapping (not sent vs ambiguous) | 60-100 |
| `PROPFIND` (calendar listing, privileges, change tokens) and `REPORT calendar-query` request building and multistatus parsing | 120-180 |
| `GET` / create-only `PUT` / conditional `PUT` / conditional `DELETE` | 80-120 |
| OX server profile (window clamping, component post-filtering, canonical URL) | 30-60 |
| **Sum** | **~300-450** |

Mapping iCalendar data into Ada's read model, the capability/reconciliation
semantics and the contract/fake-server tests are needed with or without
python-caldav. Using python-caldav would replace roughly the rows above, in
exchange for an AGPL transitive dependency and a second HTTP stack that Ada
would also have to review and keep proxy-independent.

### Recurrence expansion (decided: R1, maintainer 2026-09-26)

OX does not expand recurrences server-side, so Ada must.

| Option | License | Assessment |
| --- | --- | --- |
| **R1 `recurring-ical-events` 3.8.2** (2026-04-30) | LGPL-3.0-or-later; pulls `x-wr-timezone` 2.0.1 (LGPL-3.0-or-later) and `click` (BSD-3-Clause) | Purpose-built and actively maintained (repository activity 2026-09); handles RRULE/RDATE/EXDATE/RECURRENCE-ID overrides and time zones. Pure Python, used unmodified as a separately installed package. Same obligation class as the existing `psycopg-binary` LGPL path (NOTICE.md). Needs an explicit copyleft adoption decision. |
| R2 Ada-owned expansion on `python-dateutil` `rrule` | Apache-2.0/BSD | No copyleft, but Ada would own override/exception/DST correctness — a classic source of silent calendar bugs. |
| R3 No expansion; treat any recurring series in range as "possible conflict" | — | Fails the conflict-detection DoD for ordinary weekly family events. |

Decision: R1. R2 remains the fallback if the LGPL obligations later prove
unacceptable for a distribution mode.

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
| **T1 Configured approximate durations between registered places** | none | **Selected for MVP (plan decision D4).** Deterministic, local, visibly approximate; unknown pairs yield "travel time unknown" instead of zero. |
| T2 Self-hosted routing engine (OSRM, Valhalla, GraphHopper) on OpenStreetMap data | none after data download | Later candidate if T1 is too laborious. Engine licenses (OSRM BSD-2-Clause and GraphHopper Apache-2.0 per GitHub; Valhalla not re-verified) and **OSM data under ODbL** (attribution, share-alike for derived databases), plus memory/disk cost on the M1/16 GB target, need their own review. |
| T3 Cloud routing APIs | addresses to a third party | Not an MVP default; would require explicit, informed egress consent. |

## 9. Credential storage (MVP-60 scope only)

Production secret management belongs to MVP-90. MVP-60 needs a safe
development path for the Ada app password:

- **S1 macOS Keychain** via `/usr/bin/security` (no new dependency): encrypted at rest, not in environment/argv/logs; host-only. **Selected (plan decision D2).**
- **S2 owner-only file** (`0600`, regular file, no symlink, outside repository and Memory root): portable to containers; plaintext on a FileVault-protected disk.
- Environment variables and command-line arguments are rejected (child-process inheritance, process listings, shell history).

## 10. IONOS probe results

### Run 1 (2026-09-26, Ada mailbox, synthetic probe calendar)

| Probe | Result | Conclusion |
| --- | --- | --- |
| P1 | 4 collections: 2 writable `VEVENT` calendars with full privileges, `getctag` and `sync-token` (Ada's default calendar and the probe calendar); 1 read-only `VEVENT` collection without `sync-token` (origin not identified); 1 `VTODO` collection. | CalDAV works with an app password of Ada's mailbox. `sync-token` (RFC 6578) is available for later incremental change detection. |
| P2 | Create-only `PUT` 201; repeated create-only `PUT` 412; same UID under another resource name 403; no `ETag` in the create response. | Provider-native create-only semantics work; UID uniqueness is enforced. Ada must `GET` after create to learn the version. |
| P3 | `GET` 200 with `ETag`; UID and resource name preserved; `X-` property preserved. | Resource-name reconciliation works. Ada may mark its own events with an `X-` property (a hint, not authority). |
| P4 | Blind overwrite 201; stale `If-Match` 412; **`If-Match` with the `ETag` just read via `GET` 412** (after the blind overwrite). | `If-Match` is honored but not required. The failed matching update is an **open anomaly**; diagnosis in run 2 (P4d–P4o). |
| P7 | Stale conditional `DELETE` 412; matching `DELETE` 204; repeated `DELETE` 404. | Conditional delete and idempotent "already absent" reporting work. |
| P8 | Events at +18 months and −3 months not returned by time-range queries. | The query window is narrower than 18 months ahead / 3 months back; boundaries in run 2. |
| P9 | Inconclusive: the IMAP host prompt received a mailbox address; the connection timed out (curl exit 28) before any login. | Rerun; the script now rejects non-hostname input. |
| P10, M1–M4 | Not run (no share link). | Needed for ADR acceptance. |

### Run 2 (2026-09-26)

P1–P3, P4a–c and P7 repeated run 1. No event from run 1 was left behind (M5).

| Probe | Result | Conclusion |
| --- | --- | --- |
| P4d–P4o | Fresh event: `GET` ETag quoted and strong; first conditional update **201** and applied; no `ETag` in the update response; ETag changes; **every later `PUT` returns 412**, including one with the fresh `GET` ETag, one with the `REPORT` ETag and one **without `If-Match`**; still one copy; stored version = first update. | The rejections do not depend on `If-Match`. The server most likely rejects content it considers stale. Probe `SEQUENCE`/`DTSTAMP` never changed; normal clients increment them. P11 (run 3) tests this. |
| P4j | `REPORT` `getetag` is **unquoted** (29 characters vs 31 quoted in the `GET` header). | Ada must normalize entity tags to the quoted form before sending `If-Match`. |
| P8 boundaries | +11 and +13 months, −20 and −40 days are returned; +18 months and −3 months are not. Direct `GET`/`DELETE` of those resources works. | Supported query window at least −40 days to +13 months. Ada uses a conservative window (−1 month, +12 months) and states the limit; its own events stay addressable by resource name. |
| P9 | IMAP login with the app password **succeeded** (curl exit 0). | The IONOS app password is **not** CalDAV-scoped; it grants access to Ada's mailbox. Residual risk accepted in ADR-0009; separate app passwords per purpose allow independent revocation. |
| P10 | Anonymous share link with `?ical=true` answers **302** (not followed in run 2). | Run 3 follows HTTPS redirects anonymously and checks for iCalendar output. |
| M2 | A read-only share link could be created. | Further options (invitation, expiry) still to report. |

### Run 3 (2026-09-26) and manual observations

The CalDAV URL prompt received the **webmail address** instead of the CalDAV
collection URL, so P1–P8 and P11 returned 404/302 and are **not evaluable**. The
probe now rejects non-CalDAV URLs and stops before any write if P1 fails.

| Item | Result | Conclusion |
| --- | --- | --- |
| P9 | IMAP login succeeded again. | Confirms run 2. |
| P10 | Anonymous link: 302 to the **web UI**; after following, HTML (also with `Accept: text/calendar` and a calendar-client User-Agent); no iCalendar. | Anonymous links are **not usable** as calendar subscriptions on IONOS. |
| M1 | The app-password dialog has only a name field. | No scope choice; matches P9. |
| M2 | Invitations offer roles **Betrachter** (read), **Überarbeiter** (read/write), **Autor** (read/write/delete), plus granular folder/read/write/delete permissions (own vs all objects). | Per-person, provider-enforced roles are available for outward sharing. |
| M3 | Subscribing asks for a password. | Family members need their **own guest credentials**; Ada's credentials must never be used on family devices (they grant Ada's whole mailbox, P9). |
| M4 | No email reached Ada; the invited address received the invitation email (maintainer's report; interpretation to be confirmed). | No unintended event notifications observed so far. |

Consequence: the outward mechanism for the MVP is **one invited guest per
family member with the Betrachter role**, not anonymous links. P12 checks guest
visibility and refused writes with the guest's own credentials.

If conditional updates stay unreliable on IONOS, the fallback to evaluate is
update as conditional `DELETE` + create-only `PUT` of a new resource inside one
durable workflow. That would change event identity for subscribers and is
non-atomic, so it is not adopted before run 2.

## 11. Evidence still required

See [the probe](../../research/calendar/README.md): the update freshness rule
(P11), guest access with the guest's own credentials (P12, M3), and,
optionally, inbound sharing (P5, P6).
