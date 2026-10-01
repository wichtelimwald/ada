# MVP-60 — Real calendar provider and full calendar management

Status: implementation
Roadmap: docs/product/mvp-roadmap.md
Depends on: MVP-00 (done)
Owner PR: https://github.com/wichtelimwald/ada/pull/39 (plan/research/ADR, merged);
S1-S3 implementation PR: https://github.com/wichtelimwald/ada/pull/44 (merged);
S4 implementation PR: https://github.com/wichtelimwald/ada/pull/48 (merged).
Further implementation PRs follow for S5 and S6-S7 (roadmap stays `ready`
until S7); S5 is the next implementation slice.

## Goal

Ada maintains the family calendar through a real provider: it reads events,
creates, updates and cancels ordinary events, detects conflicts including
approximate travel time, and never duplicates or invents a real-world outcome.
The first provider is **IONOS Mail Business** (maintainer decision,
2026-09-26); the architecture stays open for further providers.

**Access model (maintainer decision, 2026-09-26):** Ada's single IONOS mailbox
owns one calendar per family member plus one family calendar and shares them
read-only with each family member's own mailbox in the same IONOS contract,
where they appear automatically. See ADR-0009 section 3 for the accepted MVP
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
  [ADR-0009](../decisions/ADR-0009-calendar-provider-integration.md) (accepted
  2026-09-26), [IONOS probe](../../research/calendar/README.md) (maintainer runs
  1–4 and manual checks M1–M6 on 2026-09-26; results in the evaluation,
  section 10).

## Scope

1. Generic CalDAV adapter behind `CalendarPort` with a declarative IONOS provider
   profile (data from the evaluation, section 10).
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

D0-D6 were decided by the maintainer on 2026-09-26; the thin Ada-owned adapter
was confirmed the same day.

| ID | Decision | Result | Status |
| --- | --- | --- | --- |
| D0 | Accept ADR-0009 | accepted 2026-09-26 after probe runs 1–4 and M6; ADR made provider-neutral (declarative CalDAV profiles instead of provider-specific adapters) | decided |
| D1 | Recurrence expansion | `recurring-ical-events` (LGPL-3.0-or-later) + `x-wr-timezone`, unmodified | decided |
| D2 | Development credential store | macOS Keychain via `/usr/bin/security` on the Mac host; owner-only `0600` file only for synthetic accounts in dev containers | decided |
| D3 | Update/cancel authority | Ada-created events within the grant; other events only with explicit per-action confirmation; Cedar policy decides; Ada records references of events it created | decided |
| D4 | Travel-time source | configured approximate durations between registered places; unknown pairs reported as unknown | decided |
| D5 | Durable payload retention | purge the workflow state after a terminal outcome and keep a content-free operation record; details below (revised after review, 2026-09-27) | decided |
| D6 | Who is busy for a family-calendar event | a family-calendar event counts as busy for every family member; participant tagging is a later refinement | decided |

### D5 in detail: operation record and recoverable purge

The existing operation-ID binding check reads the action binding from the DBOS
workflow input; `DBOS.delete_workflow` removes that input. The purge therefore
needs a replacement record and a crash-safe order:

- **Operation record** (Ada-owned local store, no event content):
  `operation_id`, action kind, **keyed action fingerprint** (HMAC-SHA-256 over
  the canonical action binding with a per-installation key kept in the
  Keychain; a plain hash of low-entropy fields such as title and time could be
  brute-forced), provider event reference, terminal provider/business outcome,
  resulting version and a **purge state** (`pending` → `workflow_deleted` →
  `scrubbed`). It also records which events Ada created (D3).
- **Binding check:** consult the operation record first, the DBOS workflow
  second. Reusing an operation ID with a different payload stays rejected after
  the purge.
- **Order:** terminal checkpoint → upsert operation record with purge state
  `pending` (idempotent) → delete the DBOS workflow → set `workflow_deleted` →
  scrub → set `scrubbed` only after the scrub **completed successfully**.
- **Recovery is driven by the operation record, not by the DBOS row.** The
  startup sweep (1) creates the missing record for any terminal workflow
  without one, (2) deletes the workflow for records still `pending`, and (3)
  scrubs for every record that is not `scrubbed`. A crash after
  `delete_workflow` but before the scrub completed therefore still leaves a
  `workflow_deleted` record that the next start finishes. Every step is
  idempotent; deleting a workflow that is already gone counts as done.
- **Scrub:** a row delete is not the whole retention story. `secure_delete`
  only helps if it is enabled on the connection **before** the delete;
  otherwise the scrub runs `VACUUM`. Then `wal_checkpoint(TRUNCATE)`, which
  truncates the WAL only on success: a BUSY or failed result leaves the record
  in `workflow_deleted`, is retried at the next sweep, and is reported by
  `ada doctor` while pending. Validation searches the SQLite main file and its
  WAL/journal for synthetic sentinel strings.
- MVP-30 encryption may replace parts of this later.

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
  Calendars are shared read-only with family members' own mailboxes; the
  provider enforces the role (M6). Appointments outside Ada's calendars are
  unknown to Ada — user-visible limitation.
- **Egress:** HTTPS to the configured provider origin only; `trust_env=False`;
  no redirects; timeouts; response-size cap; bounded time ranges.
- **Untrusted content:** server XML (DOCTYPE rejected) and event text are data.
  Descriptions are not read into model context by default. Deterministic
  complexity limits (components/properties per response, expanded occurrences
  per series and per query, lazy expansion against that budget) fail closed;
  a small recurrence rule must not turn into CPU or memory exhaustion.
- **Failure modes:** not-sent → `failed`/not attempted; sent-but-unknown →
  reconcile per ADR-0009 section 6 → `committed` only with operation-marker
  evidence, otherwise not-applied (retry with the same precondition) or
  `ambiguous`; change after approval → explicit conflict, never overwrite;
  provider unavailable → reported, no stale data.
- **Durable state:** D5 (operation record, recoverable purge, residue checks).
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
  `CancelCalendarEventProposal(event_ref, base_version)`; `base_version` holds
  the approved entity tag and `SEQUENCE`. It is part of the action binding and
  the only `If-Match` precondition Ada ever sends for that operation, so a
  change after approval becomes a conflict instead of a clobber.
- Operation marker: a non-semantic `X-` property derived from the
  `OperationId`, written where the profile confirms preservation (IONOS: yes).
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

Each slice is independently testable. PR grouping used: S1-S3, S4, then S5 and
S6-S7 (roadmap `done` only in the last PR).

- **S0 Evidence:** maintainer creates the Ada calendars' probe counterpart and an
  outward share, runs the IONOS probe; results recorded in the PR and the
  evaluation; capabilities and limits fixed; ADR-0009 accepted. **Done
  2026-09-26** (runs 1–4, M6).
- **S1 Domain and port: done.** `CalendarRef`/`CalendarAudience`/
  `CalendarAccessMode`, `EventRef`, `EventVersion`, and the read-model
  additions (`version`, `busy`, `all_day`, `recurring`, `has_attendees`) are
  added to `src/ada/ports/calendar.py`. Scoping decision: the update/cancel
  proposal types, `calendar.update`/`calendar.cancel` Cedar actions, the
  per-operation-kind capability split, and the availability-view type are
  deferred to S4/S5 rather than added unused now, to avoid dead code ahead of
  their wiring; `EventRef`/`EventVersion` are exercised starting S2/S3 instead.
  Shared contract suite: `tests/calendar_port_contract.py`, run against the
  in-memory adapter (`tests/test_in_memory_calendar_contract.py`) and the new
  CalDAV adapter (`tests/test_caldav_contract.py`). Architecture-boundary test
  extended in `tests/test_architecture_boundaries.py` to forbid `httpx2`,
  `icalendar`, `recurring_ical_events`, `x_wr_timezone` in core/ports.
- **S2 CalDAV read path: done.** Generic adapter at
  `src/ada/adapters/caldav/` (`profile.py` declarative `IONOS_PROFILE`,
  `dav_client.py` hardened transport + `PROPFIND`/`REPORT`/`GET`/create-only
  `PUT`, `mapping.py` iCalendar mapping + recurrence expansion + complexity
  budget, `adapter.py` orchestration). `icalendar` 7.3.0,
  `recurring-ical-events` 3.8.2, and `x-wr-timezone` 2.0.1 adopted after the
  focused review in
  `docs/research/caldav-parsing-dependencies-review.md` and recorded in
  NOTICE.md. Tests: `tests/test_caldav_read_path.py` (window clamping,
  canonical-URL adoption via the contract suite, entity-tag normalization,
  recurrence expansion, all-day handling, the three complexity-budget limits,
  DOCTYPE rejection, oversized-response rejection, wrong-origin-href
  rejection, malformed iCalendar).
- **S3 CalDAV create: done.** Deterministic non-semantic UID/resource name
  and operation marker derived from `OperationId`
  (`mapping.derive_event_uid`/`derive_resource_name`/`derive_operation_marker`),
  create-only `PUT`, 412 reconciliation by `GET` + marker match, read-back
  after create (no `ETag` in the IONOS create response). A 403 (duplicate
  UID under a different resource name) intentionally stays `ambiguous`
  without a GET: it cannot happen from Ada's own deterministic naming, and
  resolving it would need a UID-based search, out of MVP scope. Per ADR-0009
  section 6 ("any 2xx status is success"), a 2xx `PUT` is unconditionally
  `COMMITTED`. The provider owns events, though: `CalendarCreateResult`
  separates the deterministic `event_ref` Ada already knows the moment the
  2xx status is known from the *verified* `event`, populated only once
  read-back actually succeeds. When read-back fails or (unexpectedly)
  reports the resource missing, the result stays `COMMITTED` with
  `event_ref` set and `event` absent — never the proposal reported as if it
  were verified provider state; `DBOSDurableCalendarActions` records the
  deterministic reference directly in that case rather than requiring a
  fabricated event. A 412 whose reconciling GET fails, by contrast,
  correctly stays `ambiguous` — the provider's own response there was
  already inconclusive. A write's response body is never read at all (its
  status alone is the provider evidence), so a body-read failure on the PUT
  response cannot affect the outcome; for read requests
  (`PROPFIND`/`REPORT`/`GET`) a body-read failure after the response headers
  already arrived (for example a timeout partway through streaming) is
  classified as `CalDAVAmbiguousTransportError` like any other post-send
  transport failure, never leaked as a raw `httpx2` exception. Tests:
  `tests/test_caldav_create.py` (read-only/unconfigured calendar fail closed
  before any request, duplicate-UID-under-different-resource stays
  ambiguous, not-attempted vs. ambiguous transport-failure classification
  including a redirect after PUT, 2xx read-back success reports a verified
  event, 2xx read-back failure/404 stays committed with only the
  deterministic reference, a PUT response body read failure still reports
  committed, 412 reconciliation fault injection stays ambiguous),
  `tests/test_caldav_read_path.py` (a REPORT body read failure after the
  response headers were already received is a typed ambiguous-transport
  error, not a raw exception), `tests/test_caldav_create_durable_action.py`
  (the same 2xx-read-back-failure case through the real
  `DBOSDurableCalendarActions` layer, proving the durable-action outcome is
  also `COMMITTED` with the deterministic reference, not just the adapter's
  own return value), and `tests/test_caldav_create_crash_recovery.py` (hard
  process kill after the provider commit recovers to exactly one event via
  `tests/dbos_caldav_crash_worker.py`, extending the pattern in
  `tests/dbos_crash_worker.py`).
  **Replay-aware outcomes (corrected after the S4 review).** The create path
  predates S4's replay awareness. A create step that crashed after the
  provider committed runs again on recovery and looks like a first execution
  from the inside, so a refusal the *replay* observed before sending (calendar
  no longer writable or configured, collection lookup failing, the PUT refused
  before it left, provider no longer declared recoverable) was reported as a
  confirmed non-commit (`failed`) although the earlier execution had
  committed; the same held for the IDEMPOTENT retry after an ambiguous first
  send (no crash needed). The create workflow now takes S4's checkpointed
  `_begin_attempt` marker before the capability check, and every such refusal
  on a replay, or on that retry, is `ambiguous` with a `..._after_possible_send`
  code (`_non_commit`, shared with update/cancel). A failing collection
  lookup before the `PUT` is a typed `REJECTED` (`collection_unavailable`)
  instead of a raw exception that ended the workflow in `ERROR` without any
  outcome. Unchanged: a 2xx is `COMMITTED`, 412 reconciles by `GET` + marker,
  the operation-ID binding, and a fresh request refused before anything could
  have been sent stays a definite `failed`. Residual until the S6/D5 operation
  record: a crash between `_begin_attempt` and the send also reads as a replay
  (this only weakens a conclusion), and a replay after a person deleted the
  committed event re-creates it and reports `committed` on that `PUT`'s own
  2xx. Tests: `tests/test_caldav_create_crash_recovery.py` (replay after a
  hard kill refused before sending in five ways stays `ambiguous` with no
  second event; unreadable 412 reconciliation stays `ambiguous`; fresh
  refusals stay `failed`), `tests/test_caldav_create_durable_action.py`
  (refused retry after an ambiguous first send), `tests/test_caldav_create.py`
  (collection lookup failure is a typed refusal).
- **S4 Update/cancel: done.** Ada-owned types in `core/actions.py`:
  `UpdateCalendarEventProposal(event_ref, base_version, changes)`,
  `CancelCalendarEventProposal(event_ref, base_version)`, `EventBaseVersion`
  (entity tag + `SEQUENCE`) and keyed action bindings that include
  `base_version` (`EventRef`/`EventVersion` moved there from the port to avoid
  a core→port import cycle; the port re-exports them). `CalendarPort` gains
  `update_event`/`cancel_event`, `CalendarChangeStatus`
  (`committed`/`conflict`/`absent`/`not_applied`/`rejected`/`ambiguous`) and
  per-operation `update_capability`/`cancel_capability` (profile data; IONOS:
  update `RECONCILABLE`, cancel `IDEMPOTENT`). `CalendarEvent` gains
  `sequence`. `CalDAVCalendarAdapter._change_event` follows ADR-0009
  section 6: fail closed before any request for an unconfigured or read-only
  calendar or an unsafe resource name; read the resource; a replayed update
  that carries this operation's marker is `committed`, checked before both
  the version comparison (which the operation's own write changed) and the
  write-scope check (which only forbids a *new* write: an event later edited
  into a recurring or attendee shape keeps its proof of the earlier commit,
  also for a multi-`VEVENT` series); a version or
  `SEQUENCE` other than `base_version` is a `conflict` without a write;
  otherwise `PUT`/`DELETE` with `If-Match: <base_version>` only, base
  `SEQUENCE` + 1, fresh `DTSTAMP` and the marker (update carries all other
  properties over unchanged); a definite 412 is a `conflict`; any 2xx is
  `committed`, with a best-effort verified read-back for updates; after an
  ambiguous send or an unexpected status the re-read decides (marker →
  `committed`; unchanged base → `not_applied`; anything else, **including
  absence**, → `ambiguous`: absence does not prove an update did not commit,
  and for a cancel it proves the goal state but not that Ada's own `DELETE`
  caused it, so it is reported as `ambiguous` with
  `event_absent_cause_unknown`). `absent` only ever means "observed before
  any send" (or a 404 answer to the first send) and is a confirmed
  non-effect. Recurring series, single occurrences, events with
  attendees and time changes on all-day events are refused before any write.
  `DBOSDurableCalendarActions.update_calendar_event`/`cancel_calendar_event`
  reuse the create workflow's operation-ID binding check, fail closed for a
  `NONE` capability, retry a provably unapplied write once with the same
  precondition and otherwise report `ambiguous`. A conflict, an absent
  event or a refusal is reported as a confirmed non-commit
  (`version_conflict`/`event_absent`/...) **only when it was observed before
  any send**. A step that crashes after the provider applied a write is
  executed again on recovery and looks identical to a first execution from
  the inside, so a checkpointed `_begin_attempt` step records the process
  lifetime that began the attempt; a send step running in a different process
  (or after its own first send, in the retry) is a *replay*. On a replay only
  `committed` (this operation's own 2xx or marker) and `not_applied`
  (unchanged base) stay conclusive; every other observation (failed read,
  changed or vanished event, refusal, non-recoverable provider) is reported
  as `ambiguous` with a `..._after_possible_send` code, because it may be a
  later change by someone else rather than proof that the earlier attempt
  did not apply. A crash between `_begin_attempt` and the send also reads as
  a replay, which only ever weakens a conclusion. Not a substitute for the
  S6/D5 operation record.
  `CalendarActionService.update_event`/`cancel_event` derive the Cedar action
  (`calendar.update`/`calendar.cancel`) and resource from the typed proposal.
  Tests: `tests/test_calendar_change_actions.py` (validation, bindings),
  `tests/test_caldav_update_cancel.py` (fake IONOS server: stale/mismatched
  `If-Match`, `SEQUENCE` rule, human edit before and between read and write,
  lost response after commit, lost request before commit, unresolvable
  reconciliation, write-scope refusals, no request for read-only calendars),
  the shared contract suite (`tests/calendar_port_contract.py`, both
  adapters), `tests/test_caldav_change_durable_action.py` (DBOS layer and
  service/Cedar wiring) and `tests/test_caldav_change_crash_recovery.py` via
  `tests/dbos_caldav_change_crash_worker.py` (hard kill after the provider
  commit: update recovers `committed` with one write; replay with a failed
  read, a stripped-marker edit, a deletion or a non-recoverable provider is
  `ambiguous`, while a marker-preserving edit (also one that adds an attendee
  or recurrence) stays `committed` with one write; cancel recovers with one `DELETE` and known absence but an
  unproven cause; fresh stale and fresh absent requests keep their definite
  `version_conflict`/`event_absent` reports). Not part of S4: the operation record and
  payload purge (S6/D5), the Ada-created-events distinction of D3 (needs the
  S6 operation record), conflict detection (S5).
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
   ID for a different payload is rejected, also after its workflow state was
   purged (D5).
3. A lost response that cannot be reconciled is reported as `ambiguous` and is
   not retried blindly (fake server; real provider where reproducible).
4. An update or cancel whose event changed after approval (webmail edit)
   reports a conflict without writing and preserves the human edit. A replay
   never sends a newer entity tag than `base_version`. After a lost response,
   Ada reports `committed` only with its operation marker on the event and
   otherwise retries (unchanged base) or reports `ambiguous`.
5. A cancel removes exactly the intended event; a repeated cancel reports the
   event as already absent, not as a fresh effect.
6. Writes to a calendar configured as not writable fail closed before any
   provider request and are reported as not performed.
7. Conflict detection finds an overlapping event, a weekly recurring
   occurrence, and a travel-time conflict from configured durations; an unknown
   place pair is reported as unknown; another person's event counts as busy
   without disclosing its details to an audience that may not see them.
8. An event created or changed by Ada appears in a family member's shared,
   read-only view of the calendar (manual check as in run 4; device refresh
   latency documented, not asserted).
9. No credential, event title or location appears in logs; ambient proxy
   variables are ignored; no request leaves for another origin.
10. After a terminal outcome and the purge sweep — also after a crash at any
    purge boundary, including after `delete_workflow` but before the scrub
    completed, and after a BUSY checkpoint — neither the SQLite main file nor
    its WAL/journal contains event titles or locations (sentinel search, D5).
11. Recurring series, occurrences and events with attendees are refused for
    writes with a clear explanation.
12. A pathological recurrence (for example `FREQ=SECONDLY`, a very large
    `COUNT` or `RDATE` list) hits the complexity budget and fails closed for
    that calendar without exhausting CPU or memory.

## Validation

S1-S3 evidence: `scripts/validate.sh` passes (compile, unit tests, `ada
doctor`); test count grows across review-fix rounds. Exact validation-to-
commit binding and current test counts are recorded in
[PR #44](https://github.com/wichtelimwald/ada/pull/44) rather than duplicated
here, where they would go stale. Independent review found and this PR fixed:
a cross-origin configured-collection auth-leak, a response-size cap applied
only after the body was already buffered, a recurrence-complexity bound that
ignored `BYHOUR`/`BYMINUTE`/`BYSECOND`, budgets enforced only after
expansion, a write-redirect misclassified as not-attempted, a non-UTC
time-range bound, floating-time silently treated as UTC, an all-day event
without `DTEND` collapsing to zero duration, and post-write read-back/
reconciliation exceptions escaping the typed outcome contract. A second
review round then found and this PR also fixed: a streamed response body
that was consumed for its size cap but discarded rather than retained
(`httpx2.ResponseNotRead` on a genuinely streamed response), a successful
2xx create that was incorrectly downgraded to `ambiguous` when read-back
failed instead of staying `committed` per ADR-0009 section 6, and a query
window that could clamp to a non-empty interval still entirely outside the
provider-supported range instead of returning no events for a
non-overlapping request. A third review round then found and this PR also
fixed: a body-read failure occurring after the response headers/status were
already received (for example a timeout while streaming a REPORT body) that
bypassed the typed transport-failure classification and could leak a raw
`httpx2` exception — write requests now never read their own (unused)
response body at all, and read requests classify a body-read failure the
same way as any other post-send transport failure — and a `COMMITTED` 2xx
create with a failed read-back that reported the *proposal* data as if it
were verified provider state; `CalendarCreateResult` now separates the
deterministic `event_ref` Ada already knows from the *verified* `event`,
populated only once read-back actually succeeds. Items below tagged S4+
remain open for later PRs.

- `scripts/validate.sh` (compile, unit tests, `ada doctor`).
- Contract suite against every `CalendarPort` adapter.
- Fake-server fixture for the **IONOS profile**, matching the recorded runs:
  create-only `PUT` (repeat 412, duplicate UID 403), stale or mismatched
  `If-Match` → 412, blind overwrite without `If-Match` accepted, `SEQUENCE`
  rule (lower → 412), unquoted `REPORT` entity tags, no `ETag` in write
  responses, query window, canonical URL alias, lossy round trip. A separate
  generic fixture (for example 409 when a server requires a missing
  precondition, as noted for self-hosted OX) only where a test needs it.
- Operation-record tests: binding enforced after purge; crash tests at every
  purge boundary — before the record upsert, after it but before
  `delete_workflow`, and **after `delete_workflow` but before the scrub
  completed**; a checkpoint that returns BUSY (for example while a reader
  holds the WAL) keeps the record pending and succeeds on a later sweep;
  residue search in the SQLite main file and WAL/journal.
- Negative recurrence tests against the complexity budget.
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
  operation-ID binding also covers update/cancel base versions and survives
  the purge; the keyed fingerprint does not leak low-entropy content.
- Concurrency: every overwrite and delete is conditional on `base_version`
  and never on a later-read entity tag.
- Resource limits: recurrence expansion and parsing stay within the budget.
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
