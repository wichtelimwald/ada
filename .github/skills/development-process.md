# Skill: Development process

Adapted from the project's existing KISS-oriented workflow and informed by Ponytail-style minimalism.

## Before implementation

1. Understand the end-to-end flow.
2. Ask whether the change is needed at all.
3. Reuse existing behavior where possible.
4. Prefer standard/platform capabilities.
5. Reuse an already-approved dependency where appropriate.
6. Choose the smallest change that satisfies the requirement.
7. Only then add new code or a new dependency.

## During implementation

- Fix root causes, not symptoms.
- Keep diffs focused.
- Make trust boundaries explicit.
- Add the smallest useful runnable verification for non-trivial behavior.
- Update an ADR when the implementation changes a documented architectural decision.

## Completion gate

Do not claim completion without concrete validation evidence. Never trade away security, privacy, accessibility, error handling, or data-loss protection to reduce code size.
