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

Accepted technology choices live in `docs/decisions/`; open capability work
lives in `docs/todo.md`. Do not duplicate a changing technology-status list
here, and do not treat a researched candidate as adopted unless an accepted ADR
or other canonical decision says so.

For significant choices:

1. Define requirements and hard gates.
2. Search the problem domain for credible maintained existing systems before proposing custom infrastructure.
3. Review licenses/distribution constraints for every serious candidate.
4. Research the candidates using current primary sources where possible.
5. State cross-capability integration assumptions.
6. Use a documented decision matrix and decision-changing prototypes where useful.
7. Reopen the comparison if new evidence or a newly discovered credible system could change the outcome.
8. Record the decision, consequences, fallback/re-open triggers, and license status in an ADR.
9. Summarize user-relevant decisions in plain language in the top-level README.
10. Only then implement.

Custom infrastructure requires an explicit explanation of why an existing library/framework/service cannot satisfy the requirement behind an Ada-owned boundary.

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
