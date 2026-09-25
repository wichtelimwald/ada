# Ada backlog

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
- [ ] Implement ADR-0008's accepted file-native Memory baseline and wire `PersonalityMemoryPort`: empty Memory seeds once from the distribution profile; existing Memory wins; personality changes are inspectable/reversible.
- [ ] From the first Memory slice, preserve separate dimensions for durable Memory kind (`preference` / `fact` / `routine` / `episode`), evidence origin (`explicit_statement` / `observed_fact` / `behavioral_observation` / `hypothesis`), and lifecycle/maturity; promotion into established Memory is explicit and inspectable.
- [ ] Implement directory/lifecycle semantics: `learning/` is the only Memory area with automatic aging/expiry/compaction and contains observed facts, behavioral observations, hypotheses and non-durable extracts/summaries; `memory/` contains established/promoted/durable content and never ages automatically.

**Gates before real household Memory (ADR-0008):**

- [x] Select the protection-domain access topology delegated by ADR-0003: host-side Memory Broker with request-scoped access; one long-lived Ada principal with every vault readable is not accepted.
- [ ] Implement and validate the host-side Memory Broker, including trusted actor/audience/authorization binding, fail-closed request scope, and proof that Ada cannot read unrelated protection domains.
- [ ] Demonstrate enforceable per-person/shared protection domains and scope-partitioned retrieval/indexes behind the broker; folders under one readable OS principal are insufficient.
- [ ] Route every model-originated Memory write/promotion through a deterministic Ada-owned validation boundary for source/trust, private-by-default scope, learning class/sensitivity, provenance/lifecycle, and contradiction/correction handling.
- [ ] Implement safe Memory write/versioning behavior: out-of-band edit capture, path-restricted history commits, same-file concurrency detection/reconciliation, lock/crash recovery, and prompt capture of Ada writes so later manual reverts remain detectable.
- [ ] Implement deterministic current/superseded/unresolved retrieval and stale-source handling; direct substring search must not promote superseded text as current truth.
- [ ] Ensure operational forgetting removes content from current authoritative retrieval and every reconstructible derived index; historical purge/backup retention remains a separate explicit operation.
- [ ] Define and validate the minimum provenance/source-reference and external-document lifecycle needed by the implemented MVP scenarios without creating duplicate hidden truth.
- [ ] Enforce source ownership: calendar/contact/document facts remain owned by their authoritative source by default; Memory persists references, derived abstractions, or explicitly requested independent copies rather than duplicate current truth.
- [ ] Implement the source/document store boundary: configure a stable per-user/audience source root/provider outside learned Memory (e.g. iCloud), reference existing durable originals in place, otherwise persist directly received files there first using a human-browsable organization such as year/month; Memory never modifies/deletes originals, and only `learning/` extracts/summaries may age.
- [ ] Measure representative Memory retrieval quality/scale and run a focused local-RAG/retrieval reuse comparison (SQLite FTS5 control plus credible modular/embedded candidates such as LlamaIndex Core, Haystack, LanceDB, or an equivalent maintained option) before writing custom retrieval infrastructure or adding FTS/vector/graph/ReMe/LangMem/Hindsight; any adopted dependency must pass its own license/security/platform review.
- [ ] Treat any RAG/FTS/vector/graph layer as a rebuildable scoped cache: retrieve candidate references, re-read current authoritative Markdown, validate lifecycle/scope, then assemble model context; stale cached chunks must never become authoritative context.
- [ ] Connect local-chat typed action proposals to the existing AdaGuard + durable-action path; do not expose direct privileged model tools.
- [ ] Guard robustness follow-up: reject invalid `AuthenticationAssurance` types as `invalid_request` rather than raising during context construction.
- [ ] Implement ADR-0007 context-aware interpretation behind Ada-owned types/ports: trusted `InterpretationContext`, raw temporal expressions, and explicit/context-derived/defaulted derivation evidence.
- [ ] Close ADR-0007 resolver adoption gates before adding a production temporal dependency: safe/reproducible Quickadd JSON artifact and license provenance (or an alternative resolver), full dependency lock, target container/Linux validation, source-span attribution, determinism, thread safety, footprint, and independent review.
- [ ] Add Dependabot configuration only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
