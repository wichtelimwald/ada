# Skill: Project continuity

## Goal

Make every material Ada work session resumable without relying on chat history and without creating a second project-status database.

The stable entry point is `docs/handover.md`. Changing facts stay in their canonical sources.

## At session start

1. Read `docs/handover.md`, `AGENTS.md`, and `.github/skills/maintainer-collaboration.md`.
2. Verify current Git/GitHub state relevant to the task:
   - default-branch head;
   - active/relevant PRs and their actual heads;
   - unresolved review threads;
   - latest validation evidence and the exact commit it covers.
3. If no current task is supplied, reconstruct the active work thread from recent open PR state and activity, prioritizing in-progress non-draft work over draft backlog, then cross-check `docs/todo.md`. Do not hard-code a current PR into the stable handover.
4. Read only the canonical documents needed for the task. Do not reload broad historical research by default.
5. Treat old chat summaries, copied SHAs, test counts, mergeability, and local scratch paths as hints until re-verified.

## During work

Persist material facts where they belong, preferably in the same focused PR:

- implementation/review/validation state -> PR description, review thread, or PR comment;
- task-specific implementation or merge authorization -> the relevant PR; never promote it into a repository-wide permission;
- backlog/priority -> `docs/todo.md`;
- architecture decision -> ADR, plus `README.md` when user-relevant;
- product scope -> `docs/product/`;
- security/privacy -> security/privacy documentation;
- dependency/license/distribution evidence -> `NOTICE.md` and the relevant evidence document;
- durable setup/workflow instructions -> the relevant setup/process document.

Do not duplicate an existing canonical fact into `docs/handover.md`, `AGENTS.md`, Copilot instructions, or another prompt merely for convenience.

## Before stopping or handing over

Perform one continuity check:

1. Is the current PR description accurate about its actual head, blockers, validation, and merge gate?
2. Are unresolved review findings visible on the PR?
3. Did any decision, priority, security/privacy boundary, dependency/license conclusion, or durable setup instruction change? If yes, update its canonical source.
4. Did the continuation procedure or source-of-truth map change? Only then update `docs/handover.md`.
5. Do not claim a test/review/merge result for a different commit than the one actually verified.

A separate handover summary should be unnecessary when these conditions are satisfied.

## Evidence discipline

- Validation evidence is commit-specific. New commits make prior runs historical, not current.
- An open PR's computed merge SHA is not proof of merge.
- Review resolution, green tests, mergeability, and maintainer merge authorization are separate facts.
- Local tool/sandbox availability is ephemeral unless it is intentionally documented as a supported setup.
- When the repository and an old handover/chat disagree, re-verify and update the canonical source rather than preserving the contradiction.
