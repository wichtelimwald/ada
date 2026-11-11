# Contributing to Ada

## Language

Code, comments, documentation, issues, commits, pull requests, and GitHub review comments are written in English.

## Working model

Follow `AGENTS.md` for branch/PR, review, security and approval gates.
Follow `.github/skills/development-process.md` for implementation workflow and KISS/YAGNI.
Keep changes focused and document verified checks in the PR.

## Product and architecture decisions

Accepted decisions live under `docs/decisions/`; open work lives in `docs/todo.md`.
For significant choices, follow the canonical evaluation and license gates in
`.github/skills/technology-evaluation.md` and `.github/skills/development-process.md`.
Document new decisions and re-open triggers in an ADR; summarize user-facing changes
in `README.md`. Do not duplicate changing technology status here.

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
