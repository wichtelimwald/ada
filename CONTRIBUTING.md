# Contributing to Ada

## Language

Code, comments, documentation, issues, commits, pull requests, and GitHub review comments are written in English.

## Working model

- Work on a branch and submit a pull request.
- Do not commit directly to `main`.
- Keep changes small, focused, and reviewable.
- Prefer root-cause fixes over workarounds.
- Follow `.github/skills/development-process.md` for KISS/YAGNI.
- Prefer reuse and standard/platform capabilities over new dependencies.
- Do not introduce technology choices that have not been researched and documented where required.
- Do not add GitHub Actions unless explicitly approved by the maintainer.
- Record PR review findings and their resolution in the PR itself.

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
3. State cross-capability integration assumptions.
4. Use a documented decision matrix.
5. Record the decision, consequences, and re-open triggers in an ADR.
6. Only then implement.

## Security and privacy

Changes that affect trust boundaries, data flows, permissions, external services, memory, model context, automation, sync/backup, or distribution must update the relevant privacy/security documentation.

Never commit secrets, personal data, real credentials, private memory, private documents, or production tokens.

## Validation

Validation is local and phase-appropriate.

During discovery/documentation, evidence can include:
- diff inspected for unintended files,
- repository links/paths checked,
- documentation checked for contradictions,
- externally sourced factual claims verified,
- no unintended workflow or dependency introduced.

After an implementation stack exists, document concrete build/test/lint/security commands and provide their results. Never invent validation evidence for checks that do not exist.
