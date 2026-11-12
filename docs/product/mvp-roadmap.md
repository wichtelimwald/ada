# Ada MVP execution roadmap

**Status:** canonical execution plan for reaching the first usable family MVP.

This document answers three questions:

1. What does "MVP complete" mean?
2. Which implementation work package is next?
3. How should a new agent select and execute a step without relying on chat history?

Detailed architecture decisions remain in ADRs. Detailed backlog items remain in
`docs/todo.md`. Exact active-PR state and validation evidence remain in GitHub.
This roadmap owns the **MVP work-package order, dependencies, completion state,
and acceptance outcome**.

## MVP product outcome

The MVP uses **email for family-facing requests** and a separate, restricted
**MVP admin chat** for initial setup and changes to permissions/grants. The
admin chat must establish trusted administrator authority outside model text;
it is not a general family chat or an email-based self-approval path. Its exact
authentication and implementation remain to be designed. The existing native
local-chat CLI is a development harness, not automatically the privileged admin
interface. General family-facing interactive chat is later, with emailed
one-time login code and/or passkey still to be selected.

**Immediate working milestone: family calendar via email.** Prioritize a
narrow live vertical slice: registered family users request ordinary calendar
information and changes by email, with narrowly scoped grants configured in
the MVP admin chat. Validate using the actual participating users/accounts,
a deliberately non-sensitive test calendar/events and a reversible trial.
Do not create fake household identities as a substitute for this acceptance.
Do not expose real calendar effects until sender verification (MVP-70),
authorization (AdaGuard), duplicate prevention and recovery gates pass.
Calendar-first progress does **not** depend on completing general Memory
learning/retrieval. The broader Family Memory and learning outcome below
remains planned; it is not a prerequisite for the first calendar trial.

The MVP is complete when the family can use Ada for these three capabilities
with the accepted privacy and authority boundaries:

1. **Family Memory including learning**
   - private Memory per person plus shared family Memory;
   - human-readable/correctable authoritative Memory;
   - controlled learning and promotion;
   - AdaGuard-enforced private/shared scopes and audience-safe disclosure;
   - Git-style edit history/versioning, not current Memory.

2. **Calendar maintenance**
   - read, create, update and cancel ordinary events through a real provider;
   - conflict detection including approximate travel time;
   - source-owned calendar truth remains separate from Memory;
   - consequential writes use AdaGuard + durable execution/reconciliation.

3. **Email interaction**
   - receive mail through an Ada-controlled channel;
   - map verified registered sender addresses to configured user identities;
   - distinguish direct instructions from forwarded/quoted/untrusted text;
   - read only scoped Memory, ask questions and send authorized replies;
   - extract appointment information and use the guarded calendar path.

The cross-cutting MVP trust requirements from product discovery remain part of
the definition of done: private/shared disclosure boundaries, action logging,
recovery, correction/forgetting, and usable pause/resume behavior.

The representative acceptance scenarios remain:
`docs/product/representative-scenarios.md`.

## Status vocabulary

- **done** — merged to `main`, reviewed, and validated for this work package.
- **ready** — dependencies are done and no active PR already owns the work.
- **blocked** — at least one required dependency is not done.
- **deferred** — intentionally outside the first MVP.

An open implementation PR may temporarily own a step even while `main` still
shows it as `ready`. Agents must therefore inspect current GitHub state before
starting duplicate work.

## Agent step-selection contract

When the maintainer says **"implement the next step"**:

1. Read `AGENTS.md`, `docs/handover.md`, this roadmap, and
   `docs/plans/README.md`.
2. Inspect open PRs and current `main`.
3. If an active non-draft PR already owns the earliest executable MVP step,
   continue that work instead of opening a duplicate.
4. Otherwise choose the first work package in canonical order whose status is
   `ready` and whose dependencies are all `done`.
5. Create/update that step's plan before implementation, then execute it under
   the normal branch/PR/review rules.

When the maintainer says **"implement the step after next"** or
**"implement the overnext step"**:

1. Determine the step that would have been selected as "next".
2. Skip it.
3. Select the next work package in canonical order that is independently
   `ready` with all dependencies already `done`.
4. Do **not** implement a blocked dependent step merely to satisfy the ordinal
   request. If no second ready step exists, report that rather than inventing
   missing architecture.

When the maintainer names a step ID explicitly, that ID wins. If its dependencies
are not complete, the agent may research/plan it but must not claim implementation
completion unless the dependency can safely be avoided by an explicit interface
boundary.

## MVP work packages

| ID | Work package | Status on main | Depends on | Parallelization / purpose |
| --- | --- | --- | --- | --- |
| MVP-00 | Core foundation | done | — | PydanticAI boundary, Cedar/AdaGuard, DBOS action semantics, local Ollama, modular monolith baseline |
| MVP-10 | File-native Memory baseline | done | MVP-00 | Current Markdown authority, `memory/` vs `learning/`, seed-once personality, conservative promotion/forget baseline |
| MVP-20 | Memory semantics, safe writes and versioning | done | MVP-10 | Close baseline residuals; define correction/forget/id semantics; safe Git-style history/edit capture/concurrency |
| MVP-30 | User- and audience-scoped Memory access | ready | MVP-20 | Scope Memory through a trusted actor/audience contract; email identity integration later in MVP-70; no Ada-managed vault encryption |
| MVP-40 | Learning pipeline and retrieval | blocked | MVP-20, MVP-30 | Trusted learning validation, class A-D handling, lifecycle rules, current-only retrieval; start simple and measure before richer RAG |
| MVP-50 | Email + Family Memory | blocked | MVP-40, MVP-70 | Connect authenticated email requests to audience-scoped Memory and learning; local chat remains a development harness |
| MVP-60 | Real calendar provider and full calendar management | ready | MVP-00 | Can proceed in parallel with Memory; connect real provider for read/create/update/cancel and preserve durable action semantics |
| MVP-70 | Email channel baseline | ready | MVP-00 | Can proceed in parallel; authenticated intake/reply channel, forwarding separation, no direct privileged execution |
| MVP-80 | Family end-to-end integration | blocked | MVP-50, MVP-60, MVP-70 | Join email/calendar/Memory; conflict detection, audience-safe briefings, representative scenarios |
| MVP-90 | MVP operational hardening and delivery | blocked | MVP-80 | Backup/restore, recovery, startup/pause/resume, security gates, packaging decision, reproducible supported setup |
| MVP | First usable family MVP | blocked | MVP-90 | All primary capabilities and acceptance scenarios pass with real family-ready protection |

### MVP-00 — Core foundation

**Outcome:** accepted replaceable runtime and security/action boundaries exist.

**Evidence:** ADR-0002 through ADR-0007, current implementation and validation on
`main`.

**DoD:** already complete for roadmap purposes. Later defects remain ordinary
backlog items and do not reopen the package unless a boundary decision changes.

### MVP-10 — File-native Memory baseline

**Outcome:** ordinary current files can act as inspectable Memory/learning
authority without becoming production household storage.

**Evidence:** merged PR #37 and ADR-0008.

**DoD:** current-file personality bootstrap, Memory/evidence dimensions,
non-clobbering baseline writes, conservative promotion, current-state forget
tombstone, development-only chat opt-in, independent review and target-Mac tests.

**Important:** this package deliberately does not make the storage safe for real
household data.

### MVP-20 — Memory semantics, safe writes and versioning

**Outcome:** complete; merged PR #41 implements the accepted safe-write/versioning
semantics and passed independent review plus Linux and target-Mac validation.

**Goal:** turn the development file adapter into a well-defined, recoverable
authoritative write/versioning layer before adding real protection domains.

**Required concept/implementation plan must cover at least:**

- explicit correction vs create semantics;
- malformed established Memory is an **integrity error**, not a silent-forget case: preserve the file, fail visibly, and require either explicit repair or a separately authorized force-forget recovery path; do not infer a filesystem failure from a parse error alone;
- entry IDs are immutable and **never reused**, including after forgetting;
- generic Memory entries use opaque, non-semantic identifiers (privacy-first random IDs; avoid time-bearing/semantic slugs). References and tombstones use only that identity. Human readability comes from current Markdown content/derived display text, not the ID;
- area/lifecycle validity before data can become current context;
- out-of-band human edit capture;
- Git-style per-domain history while keeping only current head/state semantically
  active;
- same-file concurrency detection and reconciliation;
- personality bootstrap no-clobber behavior;
- crash durability including file + directory persistence semantics;
- fd-based/no-follow file access appropriate to the supported platform;
- create-only behavior on storage without hard-link support;
- idempotent/repeated forget semantics, including an explicit already-forgotten result rather than treating it as a fresh state change.

**DoD:** deterministic tests prove no silent overwrite of a human correction
that is already visible at Ada's final pre-publication revision check, no stale
re-promotion, no history rehydration, and no ambiguous write outcome for the
supported local storage profile. A non-cooperating human save that lands after
that final check but before same-working-tree publication is a documented MVP-20
residual; MVP-30 must evaluate the commit-based multi-workspace model and remove
obsolete shared-working-tree safeguards if that model is selected.

### MVP-30 — User- and audience-scoped Memory access

**Goal:** Ada uses and discloses only data permitted for the trusted actor,
intended audience and task. This is an application-level authorization boundary,
not macOS process isolation or Ada-provided encryption (ADR-0012).

**Plan must decide and prove:**

- trusted actor/audience supplied by an authenticated channel or the restricted
  MVP admin chat, independent of the model; the email verification mechanism
  is an MVP-70 decision, not a blocker for the Memory interface itself;
- deterministic AdaGuard/application checks for private and shared reads, writes,
  source-provider access, retrieval, model context and response disclosure;
- reuse S1's MemoryBrokerPort scope contract if helpful, without imposing a
  separate process, IPC, Keychain service or encrypted volume;
- private-by-default logical scopes with explicit sharing, including indexes and
  minimized derivatives; no unrestricted model filesystem tools;
- independent source/document providers respecting the same scopes;
- current Markdown and Git history preserved, including Git executable-config safety;
- human/Ada write concurrency model: evaluate separate worktrees/commits without
  assuming normal human editors follow a synchronization protocol; remove
  redundant MVP-20 guards if a superior mechanism is accepted;
- restart/recovery and operator-managed backup/restore responsibilities;
- explicit residual that same-user host applications or fully compromised
  Ada code can read locally accessible files outside scoped APIs.

**DoD:** Ada's trusted access path enforces permitted scopes with deterministic
negative regression checks; with real registered users and non-sensitive pilot
data, later end-to-end acceptance verifies no unauthorized Memory disclosure.
Ambiguous identity fails closed; history/recovery, concurrency and backup
responsibilities are addressed. No claim of Mac-level isolation or encryption.
No fabricated family identities are an MVP acceptance substitute.

### MVP-40 — Learning pipeline and retrieval

**Goal:** let Ada learn without turning inference into authority.

**Plan must cover:**

- trusted source/event -> evidence -> optional hypothesis -> Ada validation ->
  established Memory;
- class A-D sensitivity policy and explicit-user confirmation binding; promotion must be bound to the exact evidence revision the user confirmed, and changed evidence requires re-confirmation before it can become established Memory;
- contradiction/correction/supersession rules;
- lifecycle/staleness rules;
- operational forgetting and no re-learning from pre-forget current evidence;
- source-owned facts vs retained abstractions;
- current-only scoped retrieval.

**Retrieval rule:** start with direct reads / SQLite FTS5 or an equivalent KISS
control. Measure representative recall and token cost before adding vector,
graph, OpenViking-style hierarchical summaries, or another framework. If scale
justifies it, the OpenViking L0/L1/L2 pattern is a candidate **derived retrieval
strategy**, never authoritative Memory.

**DoD:** representative synthetic learning/correction/contradiction/forget
scenarios pass across protection domains and restarts.

### MVP-50 — Email + Family Memory

**Goal:** make authenticated email Ada's family-facing interface to current
scoped Memory and its learning lifecycle. The local chat CLI remains a
development-only harness and is not a second family-facing channel.

**Plan must cover:**

- reuse MVP-70's verified registered sender identity and intended recipient
  audience (recipient address is an audience hint, not permission);
- trusted actor/audience policy-scoped context acquisition;
- minimum relevant Memory content, private/shared disclosure and source scope;
- trusted confirmation path for remember/correct/forget within allowed grants;
- learning evidence from email interaction;
- no model-direct privileged Memory tools;
- local model failure/restart behavior and email reply outcome truth;
- routine requests operate only within previously configured narrow grants;
  **new, revoked or expanded grants go through the restricted MVP admin chat**,
  never ordinary email or model output; its trusted admin authority is a
  prerequisite before that workflow is enabled;

**DoD:** end-to-end checks with actual registered household accounts and
deliberately non-sensitive content confirm permitted responses and denial of
cross-user requests; manual Memory corrections affect later replies when
Memory integration is enabled. Contract tests remain useful but are not a
substitute for live acceptance.

### MVP-60 — Real calendar provider and full calendar management

**Goal:** replace the synthetic provider with one supported real provider while
retaining Ada-owned action semantics.

**First provider:** IONOS Mail Business (maintainer decision, 2026-09-26);
further CalDAV providers are added through provider profiles, other protocols
through separate adapters (ADR-0009).
**Step plan:** [MVP-60](../plans/MVP-60-real-calendar-provider.md);
architecture: ADR-0009 (accepted).

**Plan must cover:**

- provider choice and least-privilege credentials;
- list/read/create/update/cancel;
- provider-native idempotency/reconciliation;
- event identity and duplicate avoidance;
- private event disclosure vs busy-time use;
- recurring-event MVP boundary;
- travel-time input/source;
- offline/provider-error behavior;
- live pilot with the actual registered participants and a dedicated
  non-sensitive calendar/test events, with explicit before/after verification
  and recovery; no real private appointment data for the initial trial.

**DoD:** real-provider acceptance proves exactly one intended side effect across
retry/restart, correct reporting of unknown outcomes, and conflict detection with
travel time.

### MVP-70 — Email channel baseline

**Goal:** email becomes Ada's **only family-facing MVP interaction channel**.

**Plan must cover:**

- Ada mailbox/account/provider;
- registered sender-address mapping to a configured user; sender authenticity verified beyond the forgeable visible `From:` header (provider/authentication evidence and fail-closed fallback);
- trusted direct instruction vs quoted/forwarded/untrusted content;
- reply recipient and disclosure controls;
- threading/idempotency;
- attachment handling as source material;
- appointment extraction into typed drafts/proposals, never direct calendar
  mutation;
- response timing while Ada is operating and pause behavior;
- no self-service broad permission grants through ordinary incoming email;
  permission creation/changes belong to a restricted MVP admin chat;
- verification of real senders and safe reply recipients before **live**
  calendar actions; provider-authentication mechanics are decided here,
  not in MVP-30.

**DoD:** real registered senders, with deliberately non-sensitive test
messages, can request an authorized calendar proposal/reply; unverified or
forwarded text cannot grant authority; retries do not duplicate replies or
calendar effects. Automated regressions complement live pilot evidence.

### MVP-80 — Family end-to-end integration

**Goal:** demonstrate that the email, calendar and Memory components form one trustworthy
family assistant.

**Required acceptance:**

- email-based calendar scenarios run end to end with the registered
  household users and non-sensitive test events; development-only chat
  scenario S6 remains a regression, not a family-channel release gate;
- email -> interpretation -> conflict check -> authorization -> calendar effect;
- verified email senders see only their allowed current Memory in replies;
- private appointment can contribute availability without leaking details;
- correction propagates to future answers without automatically mutating a source
  system;
- family briefing is audience-safe;
- approximate travel assumptions remain visible;
- pause/restart does not invent outcomes.

**DoD:** a small, opt-in pilot with real registered household users and
non-sensitive family-calendar data passes the authentication, permission,
idempotency, recovery and response checks. Broader personal Memory/learning
and real private calendar contents remain gated until separately validated.

### MVP-90 — Operational hardening and delivery

**Goal:** make the MVP repeatably usable rather than a developer demonstration.

**Plan must cover:**

- startup/stop/pause/resume;
- family Mac sleep/offline behavior;
- operator-controlled Memory and edit-history backup/restore test;
- secret management;
- operational logging without sensitive leakage;
- supported installation/update shape;
- packaging/release architecture;
- reproducibility gates appropriate to the chosen artifact.

The blocked draft PR #33 may be revisited here **only after** packaging/distribution
shape is decided.

**DoD:** clean supported setup, restore/recovery drill, privacy/security checks,
and documented operator workflow all pass.

## Step-level plan requirement

Every non-trivial work package above must have a step plan under `docs/plans/`
before substantial implementation. Use the process and template in
`docs/plans/README.md`.

The step plan is not a second backlog. It contains the temporary detail needed
to execute that package: evidence, decisions, slices, tests, risks, and review
criteria. Durable decisions graduate to ADR/product/security docs; remaining
follow-ups graduate to `docs/todo.md`.

A step may need a research/ADR PR before its implementation PR. That is expected
when a security boundary, dependency, external provider, file format, or release
shape is still undecided.

## After the MVP

These are deliberately outside the first MVP and are not selected by the
"next MVP step" algorithm.

| ID | Follow-up | Initial direction |
| --- | --- | --- |
| POST-10 | Long-running task tracking / missions | Re-evaluate Pizza Bot and NOMAD against the working Ada runtime; keep AdaGuard, action truth and Memory boundaries independent |
| POST-20 | Speech input and output | Evaluate local-first STT/TTS, wake/listening/privacy implications and interruption UX |
| POST-30 | Animated avatar | Add as a face/presentation layer without coupling it to authority or Memory |
| POST-40 | Untis integration | Revisit direct WebUntis/API options after email/calendar flows are stable; school data gets its own access/disclosure review |
| POST-50 | Interactive authenticated chat | Provide family-facing chat after the email-only MVP; evaluate emailed one-time login codes and/or passkeys with trusted session/audience binding, revocation and approval semantics |

Ternary Bonsai 2 remains a later local-model benchmark candidate rather than an
MVP dependency. Google Artemis and GLM-5.3-FlashX are not current Ada priorities.

## Maintaining this roadmap

- Change a package to `done` only in the implementation PR that actually
  completes and validates it.
- If scope materially changes, update this roadmap and the owning product/ADR
  documents in the same reviewed change.
- Do not copy volatile head SHAs, test counts, or open findings here.
- Persist residual implementation findings in `docs/todo.md`, not only in a
  merged PR discussion.
- Before starting work, always re-check GitHub for an active PR that already owns
  the selected package.
