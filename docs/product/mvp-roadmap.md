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

The first MVP is complete when the family can use Ada for these four primary
capabilities with the already accepted privacy and authority boundaries:

1. **Family Memory including learning**
   - private Memory per person plus shared family Memory;
   - human-readable/correctable authoritative Memory;
   - controlled learning and promotion;
   - encrypted-at-rest protection domains;
   - Git-style history/versioning per protection domain, without treating history
     as current Memory.

2. **Local chat**
   - local text interaction;
   - identity/audience-aware access to permitted Memory;
   - no implicit cloud egress;
   - consequential actions still cross AdaGuard and durable-action boundaries.

3. **Calendar maintenance**
   - read, create, update and cancel ordinary events through a real provider;
   - conflict detection including approximate travel time;
   - source-owned calendar truth remains separate from Memory;
   - consequential writes use AdaGuard + durable execution/reconciliation.

4. **Email communication**
   - receive mail through an Ada-controlled channel;
   - distinguish trusted sender instructions from forwarded/untrusted content;
   - ask questions and send authorized replies;
   - extract appointment information and hand consequential calendar changes to
     the normal guarded action path.

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
| MVP-20 | Memory semantics, safe writes and versioning | ready | MVP-10 | Close baseline residuals; define correction/forget/id semantics; safe Git-style history/edit capture/concurrency |
| MVP-30 | Memory Broker, protection domains and encryption | blocked | MVP-20 | Enforce private/shared domains, request-scoped broker access, encrypted-at-rest per-domain storage/history |
| MVP-40 | Learning pipeline and retrieval | blocked | MVP-20, MVP-30 | Trusted learning validation, class A-D handling, lifecycle rules, current-only retrieval; start simple and measure before richer RAG |
| MVP-50 | Chat + Family Memory | blocked | MVP-40 | Identity/audience-aware local chat using real protected family Memory and learning |
| MVP-60 | Real calendar provider and full calendar management | ready | MVP-00 | Can proceed in parallel with Memory; connect real provider for read/create/update/cancel and preserve durable action semantics |
| MVP-70 | Email channel baseline | ready | MVP-00 | Can proceed in parallel; authenticated intake/reply channel, forwarding separation, no direct privileged execution |
| MVP-80 | Family end-to-end integration | blocked | MVP-50, MVP-60, MVP-70 | Join chat/email/calendar/Memory; conflict detection, audience-safe briefings, representative scenarios |
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

**DoD:** deterministic tests prove no silent overwrite, stale re-promotion,
history rehydration, lost human correction, or ambiguous write outcome for the
supported local storage profile.

### MVP-30 — Memory Broker, protection domains and encryption

**Goal:** make real private/shared family Memory storage technically enforceable.

**Plan must decide and prove:**

- protection domains for each person and family-shared Memory;
- broker request contract and trusted actor/audience binding;
- no standing all-vault access in normal runtime paths;
- encryption-at-rest/key ownership and unlock behavior;
- encrypted Git-style history/versioning per domain without making Git an auth
  boundary;
- separately configurable source/document providers per domain;
- backup/restore responsibilities for encrypted vaults;
- cross-domain negative tests and residual threat model.

**DoD:** synthetic private domains cannot read or disclose each other through
normal/model-driven paths; shared access is explicit; encrypted storage/history
survives restart and restore.

### MVP-40 — Learning pipeline and retrieval

**Goal:** let Ada learn without turning inference into authority.

**Plan must cover:**

- trusted source/event -> evidence -> optional hypothesis -> Ada validation ->
  established Memory;
- class A-D sensitivity policy and explicit-user confirmation binding;
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

### MVP-50 — Chat + Family Memory

**Goal:** local chat becomes a real family-facing Memory client rather than an
ephemeral development harness.

**Plan must cover:**

- authenticated/selected actor and audience;
- broker-scoped context acquisition;
- minimum relevant Memory context;
- private vs family-shared disclosure;
- trusted confirmation path for remember/correct/forget;
- learning evidence from interaction;
- no model-direct privileged Memory tools;
- local model failure/restart behavior.

**DoD:** multiple synthetic family identities receive different permitted
contexts; manual Memory corrections affect the next interaction; unauthorized
private content never appears in shared chat.

### MVP-60 — Real calendar provider and full calendar management

**Goal:** replace the synthetic provider with one supported real provider while
retaining Ada-owned action semantics.

**Plan must cover:**

- provider choice and least-privilege credentials;
- list/read/create/update/cancel;
- provider-native idempotency/reconciliation;
- event identity and duplicate avoidance;
- private event disclosure vs busy-time use;
- recurring-event MVP boundary;
- travel-time input/source;
- offline/provider-error behavior;
- tests without real personal event fixtures.

**DoD:** real-provider acceptance proves exactly one intended side effect across
retry/restart, correct reporting of unknown outcomes, and conflict detection with
travel time.

### MVP-70 — Email channel baseline

**Goal:** email becomes Ada's first external asynchronous interaction channel.

**Plan must cover:**

- Ada mailbox/account/provider;
- sender authentication/allowlist semantics beyond visible `From:`;
- trusted direct instruction vs quoted/forwarded/untrusted content;
- reply recipient and disclosure controls;
- threading/idempotency;
- attachment handling as source material;
- appointment extraction into typed drafts/proposals, never direct calendar
  mutation;
- response timing while Ada is operating and pause behavior.

**DoD:** synthetic authorized email can produce a safe reply or calendar proposal;
forwarded text cannot grant authority; retry does not send duplicate replies.

### MVP-80 — Family end-to-end integration

**Goal:** demonstrate that the individually working channels form one trustworthy
family assistant.

**Required acceptance:**

- representative scenarios S1-S6 pass end to end where in MVP scope;
- email -> interpretation -> conflict check -> authorization -> calendar effect;
- chat and email observe the same allowed current Memory;
- private appointment can contribute availability without leaking details;
- correction propagates to future answers without automatically mutating a source
  system;
- family briefing is audience-safe;
- approximate travel assumptions remain visible;
- pause/restart does not invent outcomes.

**DoD:** a synthetic household acceptance suite passes, followed by a deliberately
small real-family pilot only after all real-data gates are closed.

### MVP-90 — Operational hardening and delivery

**Goal:** make the MVP repeatably usable rather than a developer demonstration.

**Plan must cover:**

- startup/stop/pause/resume;
- family Mac sleep/offline behavior;
- encrypted-vault backup/restore test;
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
