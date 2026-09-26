# Ada backlog

The canonical MVP work-package order, dependencies, and step-selection rules live
in [the MVP execution roadmap](product/mvp-roadmap.md). This file owns detailed
backlog/gate items; the roadmap owns which MVP package comes next.


## P0 — Product discovery

- [x] Run the Ada product discovery interview.
- [x] Save the resulting questionnaire under `docs/product/`.
- [x] Derive a feature inventory and classify MVP / V1 / later / nice-to-have / out-of-scope.
- [x] Confirm target user, primary end-to-end MVP journey, and desired "Jarvis-like" interaction qualities.
- [x] Confirm privacy/cloud stance at product level, including bystander capture and non-obvious egress.
- [x] Confirm initial platform and real hardware constraints without selecting a UI framework.
- [x] Confirm distribution ambition and realistic maintainer/time budget.
- [x] Create a synthetic representative MVP scenario set for architecture and acceptance testing.
- [x] Define Ada's baseline personality and Lovelace-inspired background without historical impersonation ([personality baseline](product/personality.md)).

Product discovery baseline: [`docs/product/interview-questionnaire.md`](product/interview-questionnaire.md).  
Representative scenarios: [`docs/product/representative-scenarios.md`](product/representative-scenarios.md).

## P1 — Cross-cutting constraints

Before final capability ADRs, document integration constraints that could make individually attractive choices incompatible. The accepted modular direction is captured in [`docs/architecture/modular-core-boundaries.md`](architecture/modular-core-boundaries.md); the items below remain open until their concrete constraints are settled:

- [x] Runtime/process topology and IPC expectations ([ADR-0003](decisions/ADR-0003-execution-topology-containerization.md)).
- [x] Durable action execution / recovery — DBOS behind Ada-owned action/outcome semantics ([ADR-0005](decisions/ADR-0005-action-ledger-durable-execution.md)).
- [ ] Packaging, installation, startup/background-operation, and update constraints.
- [x] Project license strategy — retain MIT after evaluating Apache-2.0, BSD-3-Clause, and OSC-1.0 reference.
- [ ] Shared resource budgets and model/artifact distribution constraints.
- [ ] Security/privacy boundaries that every capability must respect.

## P2 — Capability decisions

Create separate evidence-based evaluations only for capabilities required by the agreed scope:

- [ ] Face — UI / interaction approach. The local CLI chat is a development/MVP interaction harness, not the final UI decision.
- [ ] Ears — wake word / speech input.
- [ ] Voice — speech output.
- [x] Brain — initial agent-runtime/orchestration foundation ([ADR-0002](decisions/ADR-0002-agent-runtime-foundation.md)).
- [x] Memory — file-native, Markdown-first authoritative Memory requiring enforceable private/shared protection domains, inspectable learning evidence/promotion, and rebuildable derived retrieval accepted by [ADR-0008](decisions/ADR-0008-memory-architecture.md).
- [ ] Hands — computer control / action runtime.
- [x] Guard — permission/policy architecture ([ADR-0004](decisions/ADR-0004-guard-permission-architecture.md)).
- [ ] Eyes — screen/camera, only if required.
- [x] Local model runtime and model strategy — self-hosted Ollama accepted; qwen3.5:9b is the configurable target-Mac baseline ([ADR-0006](decisions/ADR-0006-local-model-runtime.md)).
- [ ] Optional cloud/privacy-broker strategy, only if required.

## P3 — Implementation foundation

- [x] Create implementation scaffold only after the relevant ADRs are accepted.
- [x] Add package/dependency management appropriate to the selected stack.
- [x] Add local validation commands.
- [x] Re-validate real local multi-turn chat on target hardware; final qwen3.5:9b run passed 50 tests and the local-chat acceptance flow, enabling ADR-0006 acceptance.
- [x] Implement ADR-0008's current-file Memory baseline and wire `PersonalityMemoryPort`: empty Memory seeds once from the distribution profile, existing/current manually edited Memory wins, and the active personality is directly inspectable in Markdown.
- [ ] Make established-Memory/personality changes safely reversible through the accepted versioning/edit-capture mechanism; current-file manual editing alone is not treated as historical rollback.
- [x] From the first Memory slice, preserve separate dimensions for durable Memory kind (`preference` / `fact` / `routine` / `episode`), evidence origin (`explicit_statement` / `observed_fact` / `behavioral_observation` / `hypothesis`), and lifecycle/maturity; promotion into established Memory is explicit and inspectable.
- [ ] Implement directory/lifecycle semantics: `learning/` is the only Memory area with automatic expiry/compaction/removal and contains observed facts, behavioral observations, hypotheses and non-durable extracts/summaries; `memory/` is never automatically removed/forgotten, but `confirmed/observed_pattern` entries may transition non-destructively to `stale`; explicit-user-confirmed knowledge never stales merely through time.

The current file-native baseline is intentionally development-only and requires an explicit `--memory-root` / `ADA_MEMORY_ROOT`. It does **not** yet provide the Memory Broker, enforceable protection domains, encryption, safe Git/versioning concurrency, automatic retention/staleness, or derived retrieval. Do not place real household Memory in it until the gates below are closed.

Implementation note: the baseline uses TOML `+++` front matter so it can be parsed with Python's stdlib `tomllib` and avoid another dependency. This is **not** a settled long-term human-editing format decision: Obsidian does not expose TOML front matter as Properties, so YAML/another representation must be reconsidered before the household Memory format is finalized.

**Gates before real household Memory (ADR-0008):**

- [x] Select the protection-domain access topology delegated by ADR-0003: host-side Memory Broker with request-scoped access; one long-lived Ada principal with every vault readable is not accepted.
- [ ] Implement and validate the host-side Memory Broker, including trusted actor/audience/authorization binding and fail-closed request scope; prove that normal/model-driven/accidental application paths cannot read unrelated domains, and document/test the accepted residual risk that a fully compromised Ada runtime can forge trusted broker context while the broker itself is trusted across the domains it serves.
- [ ] Demonstrate enforceable per-person/shared protection domains and scope-partitioned retrieval/indexes behind the broker; folders under one readable OS principal are insufficient.
- [ ] Route every model-originated Memory write/promotion through a deterministic Ada-owned validation boundary for source/trust, private-by-default scope, learning class/sensitivity, provenance/lifecycle, and contradiction/correction handling.
- [ ] Before exposing `remember_explicit` / promotion through any user- or model-facing path, bind `EXPLICIT_USER` to an Ada-owned trusted confirmation event and enforce class-C sensitive-data / class-D secret handling; the file store itself must not infer those facts from caller-supplied flags.
- [ ] Implement safe established-Memory write/versioning behavior: out-of-band edit capture, path-restricted history commits, same-file concurrency detection/reconciliation, lock/crash recovery, and prompt capture of Ada writes so later manual reverts remain detectable.
- [ ] Close file-native baseline residuals before any user/model-facing generic Memory write path: treat malformed established Memory as a visible integrity error (preserve it; require explicit repair or a separately authorized force-forget recovery path rather than silently deleting it); use immutable opaque/non-semantic generic entry IDs and never reuse an ID after forgetting; ensure tombstones/references carry no semantic/sensitive slug; define idempotent repeated-forget return semantics. Human-readable display text should come from current Markdown content or derived presentation, not from the identifier.
- [ ] Harden file access/publication for the supported protected-storage profile: fd-based no-follow reads to close the remaining symlink TOCTOU window; directory durability semantics (including directory fsync / macOS durability behavior); personality bootstrap must be create-only/no-clobber under concurrency; define a create-only fallback for filesystems/providers without hard-link support instead of silently assuming `os.link`.

- [ ] Ensure normal Memory retrieval/learning uses only current state and never consults Git history, snapshots, or backups as active Memory/evidence; historical retention/purge remains a separate operations/privacy policy.
- [ ] Implement deterministic current/superseded/unresolved retrieval and stale-source handling; direct substring search must not promote superseded text as current truth.
- [ ] Before generic Memory entries are consumed by retrieval/context assembly, enforce per-area lifecycle/currentness invariants so provisional, contradicted, superseded or otherwise non-current entries cannot be returned as established current Memory.
- [ ] Ensure operational forgetting removes content from current authoritative retrieval and every reconstructible derived index, and removes/neutralizes pre-forget `learning/` evidence so forgotten knowledge cannot be silently re-promoted; historical purge/backup retention remains a separate explicit operation.
- [ ] Define and validate the minimum provenance/source-reference and external-document lifecycle needed by the implemented MVP scenarios without creating duplicate hidden truth.
- [ ] Enforce source ownership: calendar/contact/document facts remain owned by their authoritative source by default; Memory persists references, derived abstractions, or explicitly requested independent copies rather than duplicate current truth.
- [ ] Implement the source/document store boundary with **independently configurable roots/providers per protection domain** (e.g. one user's iCloud, a separate family-share, or an external/encrypted volume); no central Ada `sources/` root is required. Reference existing durable originals in place. Persist a directly received file only when the user asks or retained durable Memory/evidence needs a resolvable original; otherwise keep it session-only. With no configured destination, durable persistence fails closed. Memory never modifies/deletes originals.
- [ ] Measure representative Memory retrieval quality/scale and run a focused local-RAG/retrieval reuse comparison (SQLite FTS5 control plus credible modular/embedded candidates such as LlamaIndex Core, Haystack, LanceDB, or an equivalent maintained option) before writing custom retrieval infrastructure or adding FTS/vector/graph/ReMe/LangMem/Hindsight; any adopted dependency must pass its own license/security/platform review.
- [ ] Treat any RAG/FTS/vector/graph layer as a rebuildable scoped cache: retrieve candidate references, re-read the current authoritative owner (Memory Markdown or source provider via the broker), validate lifecycle/maturity/evidence origin/scope, label hypotheses/observations provisional, and treat unavailable-source cached values only as last-known/unverified.
- [ ] Connect local-chat typed action proposals to the existing AdaGuard + durable-action path; do not expose direct privileged model tools.
- [ ] Guard robustness follow-up: reject invalid `AuthenticationAssurance` types as `invalid_request` rather than raising during context construction.
- [ ] Implement ADR-0007 context-aware interpretation behind Ada-owned types/ports: trusted `InterpretationContext`, raw temporal expressions, and explicit/context-derived/defaulted derivation evidence.
- [ ] Close ADR-0007 resolver adoption gates before adding a production temporal dependency: safe/reproducible Quickadd JSON artifact and license provenance (or an alternative resolver), full dependency lock, target container/Linux validation, source-span attribution, determinism, thread safety, footprint, and independent review.
**Gates before real calendar data (MVP-60, [step plan](plans/MVP-60-real-calendar-provider.md)):**

- [ ] Accept or revise [ADR-0009](decisions/ADR-0009-calendar-provider-integration.md) (IONOS Mail Business via a provider-neutral CalDAV adapter; Ada-owned calendars shared outward). Recurrence expansion (`recurring-ical-events`, LGPL) and the Keychain development credential store were decided on 2026-09-26.
- [ ] Run the [IONOS CalDAV probe](../research/calendar/README.md) with synthetic calendars and record the results; usable outward sharing to family members is decision-changing.
- [ ] Complete the focused dependency reviews for `icalendar`, `recurring-ical-events` and `x-wr-timezone` and record them, including LGPL distribution obligations, in NOTICE.md before adding the dependencies.
- [ ] Minimize durable workflow state for real event data (no titles/locations retained after a terminal outcome), as required by ADR-0005.

- [ ] Add Dependabot configuration only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
