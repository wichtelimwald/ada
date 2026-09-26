# ADR-0009: Integrate calendars through a provider-neutral CalDAV adapter, starting with IONOS Mail Business

- **Status:** Accepted
- **Date:** 2026-09-26
- **Roadmap:** MVP-60 ([step plan](../plans/MVP-60-real-calendar-provider.md))
- **Evidence:** [calendar provider evaluation](../research/calendar-provider-evaluation.md) (including the IONOS probe results), [IONOS probe](../../research/calendar/README.md)

## Context

MVP-60 replaces the synthetic calendar with one real provider while keeping
Ada-owned action semantics (ADR-0005), Guard authority (ADR-0004), source
ownership of calendar facts (ADR-0008), and replaceable adapters (ADR-0003).

The maintainer selected **IONOS Mail Business** as the first provider. The
family gets **one** provider account, for Ada. Further providers must remain
addable later without changing Ada's domain semantics.

This ADR records decisions. How a specific provider behaves is evidence, not
decision content: IONOS's observed behavior is documented in the evaluation and
becomes data of the IONOS provider profile during implementation.

## Decision

### 1. Protocol and first provider

Ada integrates calendars through **CalDAV (RFC 4791)**. The first provider is
IONOS Mail Business, which exposes CalDAV. Proprietary provider APIs are not
used where CalDAV suffices.

### 2. Adapter architecture: one CalDAV adapter, declarative provider profiles

- `CalendarPort` stays provider-neutral and grows only Ada-owned types:
  calendar/event references, a read model that separates **availability**
  from **details**, typed create/update/cancel proposals, and per-operation
  duplicate-safety capabilities. Provider types (iCalendar objects, XML,
  HTTP responses) never cross the adapter boundary.
- Ada has **one generic CalDAV adapter**. Differences between CalDAV providers
  are captured in a **declarative provider profile**: data such as the
  endpoint, the supported query window, entity-tag normalization and the
  declared capabilities. A profile contains no code. IONOS is the first
  profile; another CalDAV provider (for example Nextcloud, Fastmail,
  mailbox.org) needs a new profile and passing contract tests, and new code
  only where evidence shows that the generic adapter cannot cover it.
- A provider with a **different protocol** (for example the Google Calendar
  API or Microsoft Graph) gets its own `CalendarPort` adapter.
- Every adapter and profile must pass a **shared `CalendarPort` contract test
  suite**. Each CalDAV profile has a fake server that reproduces its
  documented behavior.
- Adapters and profiles are selected explicitly in Ada's configuration and
  composition root. **Runtime discovery or loading of third-party plugins**
  requires a separate ADR with a trust and review model (AGENTS.md; ADR-0003:
  a new adapter receives no authority automatically).

### 3. Access topology: Ada-owned calendars (maintainer decision)

- Ada's own provider account holds **one calendar per family member and one
  family calendar**. Ada is their owner and regular writer.
- The maintainer creates these calendars once. Ada's runtime does not create
  or delete calendars.
- Each calendar is shared **read-only** with the relevant family members'
  own provider accounts. Changes go through Ada or, as an administrative
  fallback, through the maintainer in the provider's web interface.
- Ada's credentials are never configured on family devices.
- Ada configuration maps each calendar to its audience (person or family) and
  write permission; the mapping feeds AdaGuard decisions and disclosure.

**Accepted MVP trade-offs:**

- All family calendars live in one provider account. Separation between family
  members relies on provider sharing roles and **AdaGuard disclosure rules**,
  not on separate accounts.
- Anyone holding Ada's credential (the Ada runtime, the maintainer) can read
  every family calendar.
- Only people with whom the provider can share see Ada's calendars (IONOS:
  mailboxes in the same contract).
- Ada knows only events in its own calendars. Appointments kept elsewhere do
  not take part in conflict detection unless entered into Ada's calendars.

**Later options** (not MVP): inbound sharing of family members' own calendars
with Ada, separate Ada accounts per protection domain (revisit with MVP-30),
access for people the provider cannot share with.

### 4. Credentials

- Ada authenticates with an **app password of its own account**, with
  two-step verification enabled. No family member credentials exist in Ada.
- Credentials are class *Secret*: never in Memory, model context, logs,
  environment variables, command-line arguments, fixtures or durable workflow
  state. The development credential lives in the macOS Keychain.
- Provider app passwords may not be limited to calendar access. Ada therefore
  uses a **separate app password per purpose** (calendar, mail) so each can be
  revoked independently.

### 5. Client implementation

- A thin Ada-owned CalDAV client on the already adopted **`httpx2`** transport
  (`trust_env=False`, HTTPS only, configured origin only, no redirects,
  timeouts, response-size cap) with standard-library XML parsing and DOCTYPE
  rejection.
- **`icalendar`** (BSD-2-Clause) for RFC 5545 parsing and serialization.
- **`recurring-ical-events`** (LGPL-3.0-or-later, with `x-wr-timezone`) for
  client-side recurrence expansion, used unmodified; NOTICE.md records the
  distribution obligations when they are added.
- python-caldav 3.x is not adopted: it hard-requires `icalendar-searcher`
  (AGPL-3.0-or-later) and a second HTTP/QUIC stack.

### 6. Write semantics

These follow the standards (RFC 4791, RFC 5545, RFC 9110) and hold for every
CalDAV provider; profiles only declare what a provider guarantees.

- **Create:** a deterministic, non-semantic UID and resource name derived from
  the `OperationId`; `PUT` with `If-None-Match: *`. A precondition failure is
  resolved by reading the resource and confirming it is Ada's. The capability
  is `IDEMPOTENT` where the profile confirms create-only semantics, otherwise
  `RECONCILABLE`.
- **Update:** read the current resource (entity tag and `SEQUENCE`), then write
  with `If-Match` (entity tag normalized to the quoted form), `SEQUENCE`
  incremented and a fresh `DTSTAMP`. A precondition failure means the event
  changed since Ada read it: it is reported as a concurrent-change conflict and
  never overwritten. Any 2xx status is success.
- **Cancel:** conditional `DELETE`. After an ambiguous outcome, an absent
  resource is reported as "already absent", not as a fresh effect.
- After every write Ada re-reads the resource to obtain its version and to
  detect provider-side changes to the stored data.
- **MVP write scope:** attendee-less, non-recurring events in Ada's configured
  calendars. Recurring series, single occurrences and events with attendees
  are read-only for Ada in the MVP and fail closed with a clear explanation.
- Connection failures before a request is sent are `failed`/not attempted;
  timeouts after sending are `ambiguous` and require reconciliation.
- Queries stay within the profile's supported time window; Ada states that
  limit to users. Ada's own events remain addressable by resource name.

### 7. Privacy

- Ada owns the calendars and sees every event in full. Per-person privacy is
  enforced by **AdaGuard** (`calendar.disclose.busy` vs
  `calendar.disclose.detail`, keyed by the calendar's configured audience) and
  by the provider's sharing roles.
- Conflict checks consume the availability view; details are not needed for
  busy-time use.
- No persistent calendar cache in the MVP; provider unavailability is
  reported, not papered over with stale data.
- Durable workflow state does not retain event titles/locations after a
  terminal outcome (ADR-0005 privacy rule; purge mechanism in the step plan).

### 8. Travel time

MVP travel time comes from **configured approximate durations between
registered places**, with no routing egress. Unknown place pairs produce an
explicit "travel time unknown" result, never an implicit zero. Self-hosted
routing and cloud APIs remain later options with their own reviews.

## Validation of this decision

Before acceptance, four maintainer-run probe runs against IONOS with a
synthetic calendar (2026-09-26) confirmed that the standard semantics above
work there, including create-only writes, conditional updates with an
incremented `SEQUENCE`, conditional deletes and read-only sharing that appears
automatically on the recipients' devices. The maintainer confirmed that a
read-only recipient cannot move events from iPhone or Mac. IONOS-specific
behavior and limits are recorded in the evaluation (section 10).

## Consequences

Positive:

- Standard protocol; further CalDAV providers need a profile, not a new adapter.
- One Ada account; no family credentials in Ada; Ada is the single regular
  writer, which keeps concurrency simple.
- One reviewed HTTP transport; no AGPL dependency.

Negative / residual risks:

- The accepted MVP trade-offs of section 3.
- A provider app password may grant more than calendar access (true for
  IONOS: it also opens Ada's mailbox).
- Read-only sharing: family members cannot edit in their calendar apps, and
  their apps' refresh settings delay visible updates.
- Ada owns a small CalDAV client, including XML and HTTP edge cases.
- Providers may convert iCalendar data lossily or support only part of RRULE.
- LGPL dependencies need their distribution obligations handled before any
  Ada-built image or installer is published (NOTICE.md).

## Re-open triggers

- A provider's sharing roles do not prevent changes from family devices.
- Conflict detection must include appointments kept outside Ada's calendars.
- People the provider cannot share with need access to Ada's calendars.
- The first provider changes or removes CalDAV or app-password support.
- A provider needs behavior that a declarative profile cannot express.
- A maintained, permissively licensed CalDAV client fits Ada's transport and
  outcome requirements better than the thin adapter.
- Third-party provider plugins are required; that needs its own ADR.
