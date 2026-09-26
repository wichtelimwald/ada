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
domain semantics.

IONOS Mail Business runs on Open-Xchange App Suite and exposes calendars via
CalDAV with mailbox credentials or app passwords. Documented OX behavior and
observations against a self-hosted OX image shape the design: provider-enforced `If-Match` concurrency, source-side
confidential/private semantics for shared calendars, no server-side recurrence
expansion, no free/busy report, bounded query windows, and lossy iCalendar
conversion. Details and sources are in the evaluation.

## Decision

### 1. Provider and protocol

Use **CalDAV (RFC 4791)** against IONOS Mail Business as the first real
calendar provider. Do not use the proprietary OX HTTP API.

### 2. Access topology and credentials

- Ada uses its **own IONOS mailbox** (the dedicated Ada identity).
- Family members **share selected calendars** with that mailbox as read-only
  or writable. Provider-side sharing is the first least-privilege boundary;
  AdaGuard remains the authority boundary for every consequential action and
  every disclosure.
- Ada authenticates with an **app password of its own mailbox** (two-step
  verification enabled). Ada never stores a family member's password.
- The credential is a secret (data class *Secret*): never in Memory, model
  context, logs, environment variables, command-line arguments, fixtures or
  DBOS state.

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
  (AGPL-3.0-or-later) and a second HTTP/QUIC stack.

### 5. Recurrence expansion — maintainer decision required

Ada must expand recurrences client-side for listing and conflict detection.
Proposed: adopt `recurring-ical-events` (LGPL-3.0-or-later, with
`x-wr-timezone` LGPL-3.0-or-later) unmodified as a separately installed
dependency, recorded in NOTICE.md with its distribution obligations. If the
maintainer rejects LGPL, Ada implements expansion on `python-dateutil` with a
dedicated recurrence test corpus instead.

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
- **MVP write scope:** attendee-less, non-recurring events in calendars the
  Ada mailbox may write. Recurring series, single occurrences of a series, and
  events with attendees are read-only for Ada in the MVP and fail closed with a
  clear explanation.
- Connection failures before a request is sent are `failed`/not attempted;
  timeouts after sending are `ambiguous` and require reconciliation.

### 7. Privacy

- Busy-time use does not require details: conflict checks consume the
  availability view; detail disclosure is decided by AdaGuard
  (`calendar.disclose.detail`), not by what Ada can technically read.
- Owners control source-side disclosure: confidential events reach Ada as
  anonymous blocks; private events are invisible to Ada and therefore cannot
  contribute to conflict detection. Ada must state this limitation to users.
- Ada keeps **no persistent calendar cache** in the MVP; provider unavailability
  is reported, not papered over with stale data.
- Durable workflow state must not retain event titles/locations beyond need
  (ADR-0005 privacy rule). The mechanism (payload purge after a terminal
  outcome vs a separate private payload store) is decided in the step plan
  after verifying DBOS 3.0.0 capabilities.

### 8. Travel time

MVP travel time comes from **configured approximate durations between
registered places**, with no routing egress. Unknown place pairs produce an
explicit "travel time unknown" result, never an implicit zero. Self-hosted
routing and cloud APIs remain later options with their own reviews.

## Acceptance conditions for this ADR

Before this ADR becomes **Accepted**:

1. The maintainer decides the recurrence-expansion license question (section 5)
   and the development credential store (Keychain vs owner-only file; see the
   step plan).
2. The IONOS probe confirms that calendars shared with the Ada mailbox are
   visible and writable/read-only as granted via CalDAV (P1, P6, M3). If not,
   the access topology is re-opened before implementation.
3. Remaining probe results (P2-P5, P7-P9, M1, M2, M4) are recorded; they tune
   capabilities and limits but do not by themselves re-open this decision.

## Consequences

Positive:

- Standard protocol; other CalDAV providers need only a server profile.
- No family credentials in Ada; owners can revoke sharing per calendar.
- One reviewed HTTP transport; no AGPL dependency.

Negative / residual risks:

- One Ada credential can read every calendar shared with Ada; a compromised
  Ada runtime exposes all of them. Protection-domain alignment is revisited
  with the Memory Broker (MVP-30).
- IONOS app passwords may not be CalDAV-scoped (probe P9/M1); then the Ada
  mailbox credential also grants mail access to Ada's own mailbox.
- Ada owns a small CalDAV client, including XML and HTTP edge cases.
- Events marked private by their owner are invisible to Ada; conflict
  detection is incomplete for them by design.
- OX's lossy conversion and limited RRULE support may alter or reject events.

## Re-open triggers

- The probe shows shared calendars are not usable via CalDAV for the Ada mailbox.
- IONOS changes or removes CalDAV/app-password support.
- The family needs a provider without CalDAV (for example Google or Microsoft
  365): add a separate `CalendarPort` adapter; the domain decision stands.
- A maintained, permissively licensed CalDAV client appears that fits Ada's
  transport and outcome requirements better than the thin adapter.
- A plugin mechanism for provider adapters is required; that needs its own ADR.
