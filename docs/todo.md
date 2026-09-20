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

Product discovery baseline: [`docs/product/interview-questionnaire.md`](product/interview-questionnaire.md).  
Representative scenarios: [`docs/product/representative-scenarios.md`](product/representative-scenarios.md).

## P1 — Cross-cutting constraints

Before final capability ADRs, document integration constraints that could make individually attractive choices incompatible. The accepted modular direction is captured in [`docs/architecture/modular-core-boundaries.md`](architecture/modular-core-boundaries.md); the items below remain open until their concrete constraints are settled:

- [x] Runtime/process topology and IPC expectations ([ADR-0003](decisions/ADR-0003-execution-topology-containerization.md)).
- [ ] Packaging, installation, startup/background-operation, and update constraints.
- [ ] Project license strategy — evaluate MIT vs Apache-2.0 with BSD-3-Clause control and OSC-1.0 reference before broader external contribution.
- [ ] Shared resource budgets and model/artifact distribution constraints.
- [ ] Security/privacy boundaries that every capability must respect.

## P2 — Capability decisions

Create separate evidence-based evaluations only for capabilities required by the agreed scope:

- [ ] Face — UI / interaction approach.
- [ ] Ears — wake word / speech input.
- [ ] Voice — speech output.
- [x] Brain — initial agent-runtime/orchestration foundation ([ADR-0002](decisions/ADR-0002-agent-runtime-foundation.md)).
- [ ] Memory — human-readable stores, agent memory, dedicated local stores, and credible hybrid alternatives.
- [ ] Hands — computer control / action runtime.
- [x] Guard — permission/policy architecture ([ADR-0004](decisions/ADR-0004-guard-permission-architecture.md)).
- [ ] Eyes — screen/camera, only if required.
- [ ] Local model runtime and model strategy.
- [ ] Optional cloud/privacy-broker strategy, only if required.

## P3 — Implementation foundation

- [x] Create implementation scaffold only after the relevant ADRs are accepted.
- [x] Add package/dependency management appropriate to the selected stack.
- [x] Add local validation commands.
- [ ] Add Dependabot configuration only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
