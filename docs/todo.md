# Ada backlog

## P0 — Product discovery

- [x] Run the Ada product discovery interview.
- [x] Save the resulting questionnaire under `docs/product/`.
- [x] Derive a feature inventory and classify MVP / V1 / later / nice-to-have / out-of-scope.
- [x] Confirm target user, primary end-to-end MVP journey, and desired "Jarvis-like" interaction qualities.
- [x] Confirm privacy/cloud stance at product level, including bystander capture and non-obvious egress.
- [x] Confirm initial platform and real hardware constraints without selecting a UI framework.
- [x] Confirm distribution ambition and realistic maintainer/time budget.

Product discovery baseline: [`docs/product/interview-questionnaire.md`](product/interview-questionnaire.md).

## P1 — Cross-cutting constraints

Before final capability ADRs, document integration constraints that could make individually attractive choices incompatible:

- [ ] Runtime/process topology and IPC expectations.
- [ ] Packaging, installation, startup/background-operation, and update constraints.
- [ ] Shared resource budgets and model/artifact distribution constraints.
- [ ] Security/privacy boundaries that every capability must respect.

## P2 — Capability decisions

Create separate evidence-based evaluations only for capabilities required by the agreed scope:

- [ ] Face — UI / interaction approach.
- [ ] Ears — wake word / speech input.
- [ ] Voice — speech output.
- [ ] Brain — reasoning / orchestration.
- [ ] Memory — human-readable stores, agent memory, dedicated local stores, and credible hybrid alternatives.
- [ ] Hands — computer control / action runtime.
- [ ] Guard — permission/policy architecture.
- [ ] Eyes — screen/camera, only if required.
- [ ] Local model runtime and model strategy.
- [ ] Optional cloud/privacy-broker strategy, only if required.

## P3 — Implementation foundation

- [ ] Create implementation scaffold only after the relevant ADRs are accepted.
- [ ] Add package/dependency management appropriate to the selected stack.
- [ ] Add local validation commands.
- [ ] Add Dependabot configuration only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
