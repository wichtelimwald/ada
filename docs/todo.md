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
- [ ] Memory — **next architecture priority**. Evaluate human-readable stores, agent memory, dedicated local stores, and credible hybrid alternatives. Must support personality bootstrap/growth, correction, provenance, export/delete, and remain external to runtime persistence.
- [ ] Hands — computer control / action runtime.
- [x] Guard — permission/policy architecture ([ADR-0004](decisions/ADR-0004-guard-permission-architecture.md)).
- [ ] Eyes — screen/camera, only if required.
- [ ] Local model runtime and model strategy — self-hosted Ollama proposed as the initial baseline, pending target-Mac chat validation ([ADR-0006](decisions/ADR-0006-local-model-runtime.md)).
- [ ] Optional cloud/privacy-broker strategy, only if required.

## P3 — Implementation foundation

- [x] Create implementation scaffold only after the relevant ADRs are accepted.
- [x] Add package/dependency management appropriate to the selected stack.
- [x] Add local validation commands.
- [ ] Re-validate the first real local multi-turn chat on target hardware after the first manual run exposed banner noise, weak history recall on a self-referential prompt, and a false "action completed" claim. Accept ADR-0006 only after the corrected path passes.
- [ ] Define/select the authoritative Memory backend and wire `PersonalityMemoryPort`: empty Memory seeds once from the distribution profile; existing Memory wins; personality changes are inspectable/reversible.
- [ ] Connect local-chat typed action proposals to the existing AdaGuard + durable-action path; do not expose direct privileged model tools.
- [ ] Add Dependabot configuration only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
