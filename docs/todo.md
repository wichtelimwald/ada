# Ada backlog

## P0 — Product discovery

- [ ] Run the Ada product discovery interview.
- [ ] Save the resulting questionnaire under `docs/product/`.
- [ ] Derive a feature inventory and classify MVP / v1 / later / nice-to-have / out-of-scope.
- [ ] Confirm target user, primary end-to-end MVP journey, and desired "Jarvis-like" interaction qualities.
- [ ] Confirm privacy/cloud stance at product level.
- [ ] Confirm initial platform scope at product level without selecting a UI framework.

## P1 — Capability decisions

Create separate evidence-based evaluations only for capabilities required by the agreed scope:

- [ ] Face — UI / interaction approach.
- [ ] Ears — wake word / speech-to-text.
- [ ] Voice — text-to-speech.
- [ ] Brain — orchestration / agent runtime.
- [ ] Memory — including Letta, Obsidian/Markdown, dedicated local store, and credible alternatives.
- [ ] Hands — computer control / action runtime.
- [ ] Guard — permission/policy architecture.
- [ ] Eyes — screen/camera, only if required.
- [ ] Local model runtime and model strategy.
- [ ] Optional cloud/privacy-broker strategy, only if required.

## P2 — Implementation foundation

- [ ] Create implementation scaffold only after the relevant ADRs are accepted.
- [ ] Add package/dependency management appropriate to the selected stack.
- [ ] Add local validation commands.
- [ ] Add Dependabot only after package ecosystems actually exist.
- [ ] Revisit ProjectAtlas vs Graphify only when repository size/complexity justifies repository indexing.

## Manual repository setup

See `docs/manual-setup.md`.
