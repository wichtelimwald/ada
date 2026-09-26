# MVP-60 — Real calendar provider and full calendar management

Status: planning
Roadmap: docs/product/mvp-roadmap.md
Depends on: MVP-00 (done)
Owner PR: https://github.com/wichtelimwald/ada/pull/39 (plan/research/ADR); implementation PRs follow ADR acceptance

## Goal

Ada maintains the family calendar through a real provider: it reads events,
creates, updates and cancels ordinary events, detects conflicts including
approximate travel time, and never duplicates or invents a real-world outcome.
The first provider is **IONOS Mail Business** (maintainer decision,
2026-09-26); the architecture stays open for further providers.

**Access model (maintainer decision, 2026-09-26):** Ada's single IONOS mailbox
owns one calendar per family member plus one family calendar and shares them
outward; family members subscribe. See ADR-0009 section 2 for the accepted MVP
trade-offs.

## Current state / evidence

- `CalendarPort` ([ports/calendar.py](../../src/ada/ports/calendar.py)) supports
  list + create + reconcile-create with a declared `ProviderCapability`.
- `DBOSDurableCalendarActions` executes one authorized create with
  reconcile-before-write, fail-closed handling for providers without
  idempotency/reconciliation, and an operation-ID binding check (ADR-0005).
- `CalendarActionService` validates → authorizes via AdaGuard → hands off to
  durable execution. Cedar already defines `calendar.create`,
  `calendar.disclose.busy` and `calendar.disclose.detail`.
- `CalendarConflictChecker` detects overlap and travel-time conflicts through
  `TravelTimePort`; only synthetic adapters exist.
- README states that the calendar path is synthetic and that durable workflow
  payloads must be reviewed before real event data is used.
- Evidence for this step: [provider evaluation](../research/calendar-provider-evaluation.md),
  [proposed ADR-0009](../decisions/ADR-0009-calendar-provider-integration.md),
  [IONOS probe](../../research/calendar/README.md) (prepared, not yet run).

## Scope

1. Generic CalDAV adapter with an OX/IONOS server profile behind `CalendarPort`.
2. Read: list configured calendars, bounded event queries, recurrence expansion,
   availability view separated from details.
3. Create, update and cancel ordinary events through AdaGuard + durable execution.
4. Provider-native duplicate prevention and reconciliation for each write kind.
5. Conflict detection over real data, including recurring occurrences, busy
   semantics and configured travel times.
6. Development credential handling and durable-state minimization for real
   event data.
7. Real-provider acceptance on IONOS with synthetic calendars.

## Non-goals

- Additional providers or a runtime plugin mechanism (ADR-0009 section 3).
- Writing recurring series/occurrences, events with attendees, invitations (iMIP).
- Email intake/replies (MVP-70); chat → executable proposal wiring (MVP-80 /
  existing backlog item).
- Persistent/offline calendar cache.
- Production secret management, packaging, pause/resume (MVP-90).
- Memory integration of calendar facts (source-owned; MVP-40/80).

## Decisions

D1-D6 were decided by the maintainer on 2026-09-26 as recommended; the thin
Ada-owned adapter was confirmed the same day.

| ID | Decision | Result | Status |
| --- | --- | --- | --- |
| D0 | Accept ADR-0009 | pending: probe P1-P4, P7, P10, M2, M3 (thin adapter confirmed 2026-09-26) | open |
| D1 | Recurrence expansion | `recurring-ical-events` (LGPL-3.0-or-later) + `x-wr-timezone`, unmodified | decided |
| D2 | Development credential store | macOS Keychain via `/usr/bin/security` on the Mac host; owner-only `0600` file only for synthetic accounts in dev containers | decided |
| D3 | Update/cancel authority | Ada-created events within the grant; other events only with explicit per-action confirmation; Cedar policy decides; Ada records references of events it created | decided |
| D4 | Travel-time source | configured approximate durations between registered places; unknown pairs reported as unknown | decided |
| D5 | Durable payload retention | purge workflow after terminal outcome (`DBOS.delete_workflow`, SQLite `secure_delete`), keeping a minimal non-sensitive operation → event-reference record (also serves D3); revisit with MVP-30 encryption | decided |
| D6 | Who is busy for a family-calendar event | a family-calendar event counts as busy for every family member; participant tagging is a later refinement | decided |

## Reuse / dependency evidence

See the evaluation. Summary:

- Reuse the adopted `httpx2` transport and DBOS; no second HTTP stack.
- Adopt `icalendar` 7.3.0 (BSD-2-Clause) after a focused dependency review
  (provenance, advisories, installed wheel license, transitive `python-dateutil`,
  `six`, `tzdata`), recorded in NOTICE.md.
- Reject python-caldav 3.x (hard AGPL-3.0-or-later transitive dependency
  `icalendar-searcher`, second HTTP/QUIC stack); reuse its documented OX
  behavior as test evidence only.
- Add `recurring-ical-events` + `x-wr-timezone` (LGPL, D1) with their
  NOTICE.md entry and distribution obligations.

## Security / privacy / authority

- **Identities:** Ada's own IONOS mailbox owns all family calendars; family
  members receive outward shares. The Ada app password is class *Secret*
  (never in Memory, prompts, logs, env, argv, fixtures, DBOS state).
- **Authority:** every create/update/cancel passes AdaGuard with the action and
  resource derived from the typed proposal. Configured calendar access modes
  are cross-checked against provider-reported privileges at startup; a mismatch
  fails closed.
- **Disclosure:** Ada sees every event in its calendars. Conflict checks use the
  availability view; details are disclosed only through
  `calendar.disclose.detail`, keyed by the calendar's configured audience.
  Share links are distributed per person and treated as bearer secrets.
  Appointments outside Ada's calendars are unknown to Ada — user-visible
  limitation.
- **Egress:** HTTPS to the configured provider origin only; `trust_env=False`;
  no redirects; timeouts; response-size cap; bounded time ranges.
- **Untrusted content:** server XML (DOCTYPE rejected) and event text are data.
  Descriptions are not read into model context by default.
- **Failure modes:** not-sent → `failed`/not attempted; sent-but-unknown →
  reconcile → `committed`/`failed`/`ambiguous`; concurrent change → explicit
  conflict, never overwrite; provider unavailable → reported, no stale data.
- **Durable state:** D5; SQLite free pages can retain deleted rows unless
  `secure_delete`/VACUUM is applied.
- **Residual risk:** one Ada credential and one provider account hold every
  family calendar (accepted MVP trade-off, ADR-0009 section 2).

## Interfaces and data ownership

Ada-owned (provider-neutral) additions; names are indicative:

- `CalendarRef`: Ada calendar key → configured provider collection, owner
  audience (person or family), configured access mode (read/write).
- `EventRef`: calendar key + provider resource name; `EventVersion`: opaque
  provider version (ETag).
- Read model: `CalendarEvent` gains `version`, `busy` (from
  `TRANSP`/`STATUS`), `all_day`, `recurring`, `has_attendees`; occurrences are
  expanded into concrete intervals. An availability view (times + calendar
  audience only) is derived for conflict checks. A `visibility` marker for
  provider-anonymized events is added only if inbound sharing is implemented.
- Proposals: `UpdateCalendarEventProposal(event_ref, base_version, changes)` and
  `CancelCalendarEventProposal(event_ref, base_version)`. The approved base
  version is part of the action binding, so a replay after a human edit
  becomes a conflict instead of a clobber.
- Capabilities: duplicate safety declared **per operation kind** (create,
  update, cancel).
- `DurableActionPort`: update/cancel alongside create.
- `TravelTimePort`: returns an estimate **or** an explicit unknown.
- Cedar: `calendar.update`, `calendar.cancel` actions with calendar-audience
  attributes.

Authority per fact: the provider owns events; Ada owns operation identity,
authorization evidence and outcome truth; household configuration owns
calendar mapping and travel durations. Nothing is written to Memory.

## Implementation slices

Each slice is independently testable. Suggested PR grouping: S1-S3, S4-S5,
S6-S7 (roadmap `done` only in the last PR).

- **S0 Evidence:** maintainer creates the Ada calendars' probe counterpart and an
  outward share, runs the IONOS probe; results recorded in the PR and the
  evaluation; capabilities and limits fixed; ADR-0009 accepted. Runs 1–4
  (2026-09-26) are recorded in the evaluation; only the manual read-only check
  M6 and the maintainer's acceptance remain.
- **S1 Domain and port:** types above, in-memory adapter updated, shared
  `CalendarPort` contract test suite, architecture-boundary test extended to
  forbid `httpx2`/`icalendar` imports in core/ports. No new dependency.
- **S2 CalDAV read path:** transport hardening, `PROPFIND` listing/privileges,
  bounded `calendar-query` with window clamping and component post-filtering,
  canonical-URL adoption, iCalendar mapping, recurrence expansion (D1),
  all-day/time-zone/floating-time handling. Tests against an in-process fake
  server (`httpx2` mock transport) that reproduces documented OX behavior.
- **S3 CalDAV create:** deterministic non-semantic UID/resource name from
  `OperationId`, create-only `PUT`, reconcile by `GET`, read-back comparison to
  detect lossy provider changes (write responses carry no ETag); DBOS
  crash/retry tests against the fake server.
- **S4 Update/cancel:** durable workflows, `If-Match` with quoted-ETag
  normalization, `SEQUENCE` stored + 1 and fresh `DTSTAMP`, 201/204 as success,
  412 as concurrent change, reconciliation semantics, Cedar actions/policies
  (D3). The fake server must reproduce the IONOS `SEQUENCE` rule.
- **S5 Conflict detection:** busy semantics, occurrences, travel table (D4),
  explicit unknown travel, availability-only inputs.
- **S6 Operations:** credential source (D2), durable payload retention (D5),
  configuration, `ada doctor` checks (reachability, privileges vs configured
  mode, no credential echo), `docs/manual-setup.md`, README, NOTICE.md.
- **S7 Real-provider acceptance:** maintainer-run on the target Mac with
  synthetic IONOS calendars.

## Acceptance / Definition of Done

Roadmap DoD: real-provider acceptance proves exactly one intended side effect
across retry/restart, correct reporting of unknown outcomes, and conflict
detection with travel time. Concretely, on IONOS with synthetic calendars:

1. A create interrupted after the provider commit and before the durable
   checkpoint (forced process kill) recovers to exactly one event and reports
   `committed`.
2. Re-submitting the same operation creates no duplicate; reusing an operation
   ID for a different payload is rejected.
3. A lost response that cannot be reconciled is reported as `ambiguous` and is
   not retried blindly (fake server; real provider where reproducible).
4. An update after a concurrent webmail edit reports a conflict and preserves
   the human edit; a replayed update never overwrites a newer version.
5. A cancel removes exactly the intended event; a repeated cancel reports the
   event as already absent, not as a fresh effect.
6. Writes to a calendar configured as not writable fail closed before any
   provider request and are reported as not performed.
7. Conflict detection finds an overlapping event, a weekly recurring
   occurrence, and a travel-time conflict from configured durations; an unknown
   place pair is reported as unknown; another person's event counts as busy
   without disclosing its details to an audience that may not see them.
8. An event created or changed by Ada appears in an outward subscription (P10
   evidence; client refresh latency documented, not asserted).
9. No credential, event title or location appears in logs; ambient proxy
   variables are ignored; no request leaves for another origin.
10. Durable state no longer holds event titles/locations after a terminal
    outcome (D5).
11. Recurring series, occurrences and events with attendees are refused for
    writes with a clear explanation.

## Validation

- `scripts/validate.sh` (compile, unit tests, `ada doctor`).
- Contract suite against every `CalendarPort` adapter.
- Fake-server tests for OX behaviors: canonical URL alias, `If-Match` 409,
  ignored `comp-filter`, 400 on free/busy, query window, lossy round trip.
- DBOS crash tests extending `tests/dbos_crash_worker.py` for create, update
  and cancel.
- Negative tests: DOCTYPE/oversized responses, redirects, proxy environment,
  wrong origin, credential sentinel never logged, malformed iCalendar.
- Opt-in real-provider acceptance (for example `ADA_CALDAV_ACCEPTANCE=1`),
  maintainer-run on the M1/16 GB target Mac; never automated in CI (no
  GitHub Actions).

## Review focus

- Outcome truth: can any path report `committed` without provider evidence, or
  retry a write whose outcome is unknown?
- Identity: UID/resource derivation is stable, non-semantic, collision-safe;
  operation-ID binding also covers update/cancel base versions.
- Concurrency: every overwrite and delete is ETag-conditional.
- Egress and transport: no proxy, redirect, or origin escape; TLS verification.
- Parsing: XML and iCalendar as untrusted input; time zones, DST, all-day,
  floating times, recurrence overrides.
- Disclosure: availability vs details; confidential/private handling; model
  context minimization; prompt injection through event text.
- Durable-state retention and SQLite residue.
- OX lossy conversion: read-back detection of provider-side changes.

## Follow-ups

To be copied to `docs/todo.md` before the implementation PRs merge:

- Provider-adapter plugin/extension mechanism with a trust/review model (own ADR).
- Second provider adapter (for example Google Calendar or Microsoft Graph) when needed.
- Writing recurring events and attendee/invitation handling (with MVP-70).
- Self-hosted routing engine evaluation if configured travel durations are insufficient.
- Offline calendar cache with explicit staleness.
- Align calendar access with protection domains / Memory Broker (MVP-30):
  inbound sharing of family members' own calendars or separate Ada accounts
  per protection domain instead of one account holding every family calendar.
- Read-only import of appointments kept outside Ada's calendars (for example
  ICS feeds) if conflict detection must cover them.
- Production credential management (MVP-90). The development adapter reads
  the app password from the Keychain service `ada-caldav` (same item as the
  probe); a separate app password is used for mail (MVP-70).
- IONOS shares calendars only with mailboxes in the same contract and offers
  no external guest passwords: decide after the MVP how people outside the
  contract get access.
