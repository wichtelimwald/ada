# ADR-0009: Integrate IONOS Mail Business through a provider-neutral CalDAV adapter

- **Status:** Proposed
- **Date:** 2026-09-26
- **Roadmap:** MVP-60 ([step plan](../plans/MVP-60-real-calendar-provider.md))
- **Evidence:** [calendar provider evaluation](../research/calendar-provider-evaluation.md), [IONOS probe](../../research/calendar/README.md)

## Context

MVP-60 replaces the synthetic calendar with one real provider while keeping
Ada-owned action semantics (ADR-0005), Guard authority (ADR-0004), source
ownership of calendar facts (ADR-0008), and replaceable adapters (ADR-0003).

The maintainer selected **IONOS Mail Business** as the first provider and
requires that further providers remain addable later without changing Ada's
domain semantics. The family gets **one** IONOS mailbox, for Ada.

IONOS Mail Business runs on Open-Xchange App Suite and exposes calendars via
CalDAV with mailbox credentials or app passwords. Documented OX behavior and
observations against a self-hosted OX image, checked by four IONOS probe
runs, shape the design: `If-Match` honored but not required, updates rejected
when their `SEQUENCE` is stale, no server-side recurrence expansion, no
free/busy report, bounded query windows, calendar sharing only with mailboxes
in the same contract, and lossy iCalendar conversion. Details and sources are
in the evaluation.

## Decision

### 1. Provider and protocol

Use **CalDAV (RFC 4791)** against IONOS Mail Business as the first real
calendar provider. Do not use the proprietary OX HTTP API.

### 2. Access topology: Ada-owned calendars (maintainer decision, 2026-09-26)

- Ada's **own IONOS mailbox** holds **one calendar per family member and one
  family calendar**. Ada is their owner and regular writer.
- The maintainer creates these calendars once in webmail. Ada's runtime does
  not create or delete calendars.
- Ada shares each calendar **read-only (role Betrachter)** with the family
  member's **own mailbox in the same IONOS contract**. The shared calendar then
  appears automatically in that person's account and calendar apps (probe run
  4, M3); nobody subscribes manually. Changes go through Ada or, as an
  administrative fallback, through the maintainer in webmail. Ada's credentials
  are never configured on family devices.
- IONOS offers no external guests with their own password and shares only with
  mailboxes in the same contract; anonymous share links lead to the web UI,
  not to iCalendar (probe runs 3–4). Neither is used.
- Ada authenticates with an **app password of its own mailbox** (two-step
  verification enabled). No family member credentials exist in Ada.
- The credential is a secret (data class *Secret*): never in Memory, model
  context, logs, environment variables, command-line arguments, fixtures or
  DBOS state. The development credential lives in the macOS Keychain (plan
  decision D2).
- Ada configuration maps each calendar to its audience (person or family) and
  write permission. That mapping feeds AdaGuard decisions and disclosure.

**Accepted MVP trade-offs:**

- All family calendars live in one provider account. Separation between family
  members depends on **which calendars are shared with whom** (provider-
  enforced roles) and on **AdaGuard disclosure rules**, not on separate
  provider accounts for the calendars.
- Only people with a mailbox in the same IONOS contract can see Ada's
  calendars. Access for anybody else is a post-MVP question.
- Anyone holding Ada's credential (the Ada runtime, the maintainer) can read
  every family calendar and Ada's mailbox.
- Ada knows only events in its own calendars. Appointments kept elsewhere
  (work or personal calendars) do not take part in conflict detection unless
  they are entered into Ada's calendars.

**Later options** (not MVP): family members share their own calendars **with**
Ada (inbound sharing), separate Ada accounts per protection domain (revisit
with MVP-30), or another mechanism for people outside the IONOS contract.

### 3. Provider-neutral boundary; CalDAV as a generic adapter

- `CalendarPort` stays provider-neutral and grows only Ada-owned types:
  calendar/event references, a read model that separates **availability**
  from **details**, typed create/update/cancel proposals, and per-operation
  duplicate-safety capabilities.
- The implementation is one **generic CalDAV adapter** with explicit
  configuration. IONOS/OX specifics live in a **server profile** (for example
  query window, component post-filtering), not in
  domain code and not in an IONOS-specific adapter.
- Provider libraries' types (iCalendar objects, XML elements, HTTP responses)
  never cross the adapter boundary.
- A **shared `CalendarPort` contract test suite** must pass for every adapter
  (in-memory fake, CalDAV against a fake OX-behaving server, and future
  adapters such as Google Calendar or Microsoft Graph).
- Adapters are selected explicitly in Ada's composition root. **Runtime
  discovery or loading of third-party provider plugins is out of scope** until
  a separate plugin trust/review decision exists (AGENTS.md; ADR-0003: a new
  adapter receives no authority automatically).

### 4. Implementation approach: thin Ada-owned CalDAV client

- Build the narrow CalDAV subset Ada needs on the already adopted **`httpx2`**
  transport (`trust_env=False`, HTTPS only, configured origin only, no
  redirects, timeouts, response-size cap) and standard-library XML parsing
  with DOCTYPE rejection.
- Adopt **`icalendar`** (BSD-2-Clause) for RFC 5545 parsing/serialization,
  pinned after its dependency review.
- Do **not** adopt python-caldav 3.x: it hard-requires `icalendar-searcher`
  (AGPL-3.0-or-later) and a second HTTP/QUIC stack. It is the only maintained
  full Python CalDAV client found; see the evaluation for the comparison and the
  estimated size of the Ada-owned subset.

### 5. Recurrence expansion (maintainer decision D1, 2026-09-26)

Ada expands recurrences client-side with **`recurring-ical-events`**
(LGPL-3.0-or-later, with `x-wr-timezone` LGPL-3.0-or-later), used unmodified
as separately installed dependencies. NOTICE.md records them and their
distribution obligations once they are added.

### 6. Action semantics

- **Create:** Ada derives a deterministic, non-semantic UID and resource name
  from the `OperationId` and writes with `PUT` + `If-None-Match: *`. IONOS
  rejects a repeated create-only `PUT` (412) and duplicate UIDs (403), so the
  capability is `IDEMPOTENT`; a 412 is resolved by reading the resource and
  confirming it is Ada's. Write responses carry no ETag; Ada reads the resource
  afterwards.
- **Update/cancel:** read the current resource (ETag and `SEQUENCE`), then
  write with `If-Match` (always sent by Ada, because IONOS does not require
  it; ETags normalized to the quoted form, because `REPORT` returns them
  unquoted), a **`SEQUENCE` of stored + 1** and a fresh `DTSTAMP`. IONOS
  rejects a `SEQUENCE` lower than the stored one with 412 and increments the
  stored value itself (probe run 4, P11). A 412 therefore means that the event
  changed since Ada read it: it is reported as a concurrent-change conflict,
  never overwritten. Updates may answer 201 or 204. Ambiguous outcomes are
  reconciled by re-reading and comparing the Ada-owned fields; unresolved
  cases stay `ambiguous`.
- **Query window:** IONOS returns events from at least 40 days back to 13
  months ahead, but not 3 months back or 18 months ahead (probe runs 2 and 4).
  Ada queries at most one month back and twelve months ahead and states this
  limit; Ada's own events stay addressable by resource name outside it.
- **MVP write scope:** attendee-less, non-recurring events in Ada's configured
  calendars. Recurring series, single occurrences of a series, and events with
  attendees are read-only for Ada in the MVP and fail closed with a clear
  explanation.
- Connection failures before a request is sent are `failed`/not attempted;
  timeouts after sending are `ambiguous` and require reconciliation.

### 7. Privacy

- Ada owns the calendars and sees every event in full. Per-person privacy is
  therefore enforced by **AdaGuard** (`calendar.disclose.busy` vs
  `calendar.disclose.detail`, keyed by the calendar's configured audience) and
  by share distribution, not by provider classification.
- Busy-time use does not require details: conflict checks consume the
  availability view.
- Ada keeps **no persistent calendar cache** in the MVP; provider unavailability
  is reported, not papered over with stale data.
- Durable workflow state does not retain event titles/locations after a
  terminal outcome (plan decision D5, ADR-0005 privacy rule).

### 8. Travel time

MVP travel time comes from **configured approximate durations between
registered places** (plan decision D4), with no routing egress. Unknown place
pairs produce an explicit "travel time unknown" result, never an implicit zero.
Self-hosted routing and cloud APIs remain later options with their own reviews.

## Acceptance conditions for this ADR

Before this ADR becomes **Accepted**:

1. ~~The maintainer decides recurrence expansion and the development credential
   store~~ — decided 2026-09-26 (D1: `recurring-ical-events`; D2: Keychain).
2. ~~The maintainer confirms the thin Ada-owned adapter over python-caldav
   (section 4)~~ — confirmed 2026-09-26.
3. ~~The IONOS probe confirms the CalDAV basics on Ada's mailbox and usable
   outward sharing~~ — runs 1–4 on 2026-09-26 confirmed P1–P3, P7, P8, P9 and
   the update rule (P11); sharing with a same-contract mailbox appears
   automatically in that person's calendar apps (M3).
4. The maintainer confirms that a family member with the Betrachter role
   cannot change or delete an event of the shared calendar from their own
   device (M6).

## Consequences

Positive:

- Standard protocol; other CalDAV providers need only a server profile.
- One Ada mailbox; no family credentials in Ada; Ada is the single regular
  writer, which keeps concurrency simple.
- One reviewed HTTP transport; no AGPL dependency.

Negative / residual risks:

- Accepted MVP trade-offs of the Ada-owned calendar model (section 2).
- IONOS app passwords are not CalDAV-scoped (probe run 2, P9): the calendar
  credential also grants access to Ada's mailbox. Ada uses separate app
  passwords per purpose so each can be revoked independently.
- Read-only sharing: family members cannot edit directly in their calendar
  apps. Apple Calendar showed changes only after a manual refresh (then almost
  immediately); automatic refresh depends on each device's fetch settings.
- Family members need a mailbox in the same IONOS contract.
- Ada owns a small CalDAV client, including XML and HTTP edge cases.
- OX's lossy conversion and limited RRULE support may alter or reject events.
- LGPL dependencies need their distribution obligations handled before any
  Ada-built image or installer is published (NOTICE.md).

## Re-open triggers

- The Betrachter role does not prevent changes from family devices (M6).
- People without a mailbox in the IONOS contract need access to Ada's
  calendars.
- Conflict detection must include appointments kept outside Ada's calendars
  (inbound sharing or a second provider adapter).
- IONOS changes or removes CalDAV/app-password support.
- The family needs a provider without CalDAV (for example Google or Microsoft
  365): add a separate `CalendarPort` adapter; the domain decision stands.
- A maintained, permissively licensed CalDAV client appears that fits Ada's
  transport and outcome requirements better than the thin adapter.
- A plugin mechanism for provider adapters is required; that needs its own ADR.
