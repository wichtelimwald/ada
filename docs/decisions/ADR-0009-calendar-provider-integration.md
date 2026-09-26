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
observations against a self-hosted OX image shape the design: provider-enforced
`If-Match` concurrency, no server-side recurrence expansion, no free/busy
report, bounded query windows, read-only outward sharing to external guests,
and lossy iCalendar conversion. Details and sources are in the evaluation.

## Decision

### 1. Provider and protocol

Use **CalDAV (RFC 4791)** against IONOS Mail Business as the first real
calendar provider. Do not use the proprietary OX HTTP API.

### 2. Access topology: Ada-owned calendars (maintainer decision, 2026-09-26)

- Ada's **own IONOS mailbox** holds **one calendar per family member and one
  family calendar**. Ada is their owner and regular writer.
- The maintainer creates these calendars once in webmail. Ada's runtime does
  not create or delete calendars.
- Family members **subscribe** to the calendars shared with them (outward
  sharing; read-only per OX documentation). Changes go through Ada or, as an
  administrative fallback, through the maintainer in webmail.
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
  members depends on **which share links/invitations each person receives**
  and on **AdaGuard disclosure rules**, not on separate provider accounts.
- Anyone holding Ada's credential (the Ada runtime, the maintainer) can read
  every family calendar.
- Share links are bearer secrets; a forwarded link discloses that calendar.
- Ada knows only events in its own calendars. Appointments kept elsewhere
  (work or personal calendars) do not take part in conflict detection unless
  they are entered into Ada's calendars.

**Later options** (not MVP): family members share their own calendars **with**
Ada (inbound sharing; the probe keeps optional checks for it), or separate Ada
accounts per protection domain (revisit with MVP-30).

### 3. Provider-neutral boundary; CalDAV as a generic adapter

- `CalendarPort` stays provider-neutral and grows only Ada-owned types:
  calendar/event references, a read model that separates **availability**
  from **details**, typed create/update/cancel proposals, and per-operation
  duplicate-safety capabilities.
- The implementation is one **generic CalDAV adapter** with explicit
  configuration. IONOS/OX specifics live in a **server profile** (for example
  query window, `If-Match` requirement, component post-filtering), not in
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
  from the `OperationId` and writes with `PUT` + `If-None-Match: *`. Recovery
  reconciles by reading that resource. The declared capability follows probe
  evidence (`IDEMPOTENT` if a repeated create-only PUT is rejected, otherwise
  `RECONCILABLE`).
- **Update/cancel:** read-modify-write with `If-Match`. A 412/409 after
  another party changed the event is reported as a concurrent-change conflict,
  never overwritten. Ambiguous outcomes are reconciled by re-reading and
  comparing the Ada-owned fields; unresolved cases stay `ambiguous`.
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
3. The IONOS probe confirms the CalDAV basics on Ada's mailbox (P1-P4, P7) and
   that outward sharing delivers the calendars to family members in a usable
   way (P10, M2, M3). If outward sharing is unusable, the access topology is
   re-opened before implementation.
4. Remaining probe results (P8, P9, M1, M4) are recorded; they tune
   capabilities and limits but do not by themselves re-open this decision.

## Consequences

Positive:

- Standard protocol; other CalDAV providers need only a server profile.
- One Ada mailbox; no family credentials in Ada; Ada is the single regular
  writer, which keeps concurrency simple.
- One reviewed HTTP transport; no AGPL dependency.

Negative / residual risks:

- Accepted MVP trade-offs of the Ada-owned calendar model (section 2).
- IONOS app passwords may not be CalDAV-scoped (probe P9/M1); then the Ada
  mailbox credential also grants access to Ada's mail.
- Read-only subscriptions: family members cannot edit directly in their
  calendar apps; subscription refresh intervals of their apps delay updates.
- Ada owns a small CalDAV client, including XML and HTTP edge cases.
- OX's lossy conversion and limited RRULE support may alter or reject events.
- LGPL dependencies need their distribution obligations handled before any
  Ada-built image or installer is published (NOTICE.md).

## Re-open triggers

- The probe shows outward sharing is unusable for family members.
- Conflict detection must include appointments kept outside Ada's calendars
  (inbound sharing or a second provider adapter).
- IONOS changes or removes CalDAV/app-password support.
- The family needs a provider without CalDAV (for example Google or Microsoft
  365): add a separate `CalendarPort` adapter; the domain decision stands.
- A maintained, permissively licensed CalDAV client appears that fits Ada's
  transport and outcome requirements better than the thin adapter.
- A plugin mechanism for provider adapters is required; that needs its own ADR.
