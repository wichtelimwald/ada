# Contributing to Ada

## Language

Code, comments, documentation, issues, commits, and pull requests are written in English.

## Working model

- Work on a branch and submit a pull request.
- Do not commit directly to `main`.
- Keep changes small, focused, and reviewable.
- Prefer root-cause fixes over workarounds.
- Prefer reuse and standard/platform capabilities over new dependencies.
- Do not introduce technology choices that have not been researched and documented where required.
- Do not add GitHub Actions unless explicitly approved by the maintainer.

## Product and architecture decisions

The project is currently in discovery. Do not assume:

- target UI framework,
- target platform strategy,
- memory implementation,
- agent/orchestration framework,
- computer-control framework,
- STT/TTS stack,
- local model runtime,
- cloud provider.

For significant choices:

1. Define requirements and decision criteria.
2. Research credible alternatives using current primary sources where possible.
3. Use a documented decision matrix.
4. Record the decision and consequences in an ADR.
5. Only then implement.

## Security and privacy

Changes that affect trust boundaries, data flows, permissions, external services, memory, model context, or automation must update the relevant privacy/security documentation.

Never commit secrets, personal data, real credentials, private memory, private documents, or production tokens.

## Validation

Validation is local. The exact commands will be documented after the implementation stack is selected. A change is not complete without evidence that its relevant checks passed.
