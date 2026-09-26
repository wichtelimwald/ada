# Ada project handover

This file is the durable entry point for continuing Ada in a new chat or agent session.

It is deliberately **not** a project-status snapshot. Volatile facts such as current branch SHAs, open findings, test counts, active PR lists, and local scratch paths belong in their canonical sources and must be re-verified. The handover stays small by pointing to those sources instead of copying them.

Repository: https://github.com/wichtelimwald/ada

## Copy-and-paste start prompt

```text
You are continuing work on Ada as a factual technical sparring partner and implementation assistant.

Repository: https://github.com/wichtelimwald/ada

Start by reading:
1. AGENTS.md
2. docs/handover.md
3. .github/skills/project-continuity.md
4. .github/skills/maintainer-collaboration.md
5. docs/product/mvp-roadmap.md when the task is about MVP progress or "next step";
6. only the task-relevant canonical documents referenced there.

Before changing anything, verify the current repository and GitHub state rather than trusting an old chat:
- default-branch head and current working branch/worktree if available;
- open pull requests relevant to the task, including PR descriptions;
- unresolved review threads and latest review state;
- validation evidence tied to the exact commit it was run against.

If no concrete current task was supplied, reconstruct the active work thread from current GitHub state: inspect recent open PRs, prioritize in-progress non-draft work over draft backlog, then cross-check docs/todo.md. Do not encode a current PR number in this handover. If more than one candidate is genuinely active, state the ambiguity instead of guessing.

Use docs/product/mvp-roadmap.md for MVP work-package order, dependencies and "next/overnext step" selection; use docs/todo.md for detailed backlog/gates, ADRs for architecture decisions, README/docs/product for product status, and the active PR for implementation/review/validation state. Step-level execution plans live under docs/plans/. Do not recreate these facts in a second summary.

Continue from the latest verified state. Do not restart settled research without new decision-relevant evidence. Preserve existing user work and follow the repository branch/PR rules. Never merge without the maintainer's explicit authorization; review or CI is not merge authorization.

During the work, persist material new facts in the canonical source that owns them. Before stopping or handing over, run the project-continuity check so another session can continue without the current chat.

Chat with the maintainer in German unless asked otherwise; repository and GitHub content remain English.
```

## Source-of-truth map

| Concern | Canonical source |
| --- | --- |
| Agent rules and development gates | `AGENTS.md`, `.github/skills/development-process.md` |
| Session continuity process | `.github/skills/project-continuity.md` |
| Maintainer collaboration preferences | `.github/skills/maintainer-collaboration.md` |
| Product direction and user-facing status | `README.md`, `docs/product/` |
| MVP execution order, dependencies, completion state | `docs/product/mvp-roadmap.md` |
| Step-level execution plans | `docs/plans/` |
| Detailed backlog and gates | `docs/todo.md` |
| Architecture decisions and status | `docs/decisions/` |
| Architecture boundaries | `docs/architecture/` |
| Security and privacy | `PRIVACY.md`, `SECURITY.md`, `docs/security/`, `.github/skills/security-privacy.md` |
| Current implementation, blockers, reviews, exact validation evidence | current Git state and the relevant GitHub PR description/review threads/comments |
| Dependency, licensing, and distribution evidence | `NOTICE.md` plus the relevant research/review document |
| Research evidence | the relevant file under `docs/research/` or `research/` |
| Durable local setup instructions | `docs/manual-setup.md` |

If a durable fact has no suitable canonical home, create or extend the narrowest appropriate document. Do not make this handover the default dumping ground.

## What must survive a chat boundary

The old one-off handover mixed several useful categories. Keep them, but in separate durable homes:

- **Maintainer preferences and working style** -> `.github/skills/maintainer-collaboration.md`.
- **Project invariants and decisions that must not be forgotten** -> their owning ADR, product, security/privacy, license, setup, or backlog document.
- **Current work state, blockers, exact validation evidence, review findings, and task/merge authorization** -> the relevant active PR.
- **Ephemeral local paths, tool availability, and scratch state** -> re-verify in the new session; persist only when they become supported setup instructions.

This keeps the important information durable without turning the handover itself into a second copy of project state.

## Continuity rule

Progress is persisted by updating the **owner of the fact**, not by continuously growing this file.

Examples:

- implementation, current blocker, review finding, or commit-specific test result -> relevant PR;
- MVP work-package order/status/dependency change -> `docs/product/mvp-roadmap.md`;
- step execution detail -> the matching file under `docs/plans/`;
- detailed backlog/gate change -> `docs/todo.md`;
- accepted/revised architecture decision -> ADR and, when user-relevant, `README.md`;
- product-scope change -> `docs/product/` and relevant backlog entry;
- security/privacy boundary change -> threat/privacy documentation;
- dependency/license/distribution finding -> `NOTICE.md` and its evidence document;
- durable development-environment instruction -> `docs/manual-setup.md`.

Update `docs/handover.md` itself only when the continuation procedure, repository entry point, or source-of-truth map changes.

## Why this is not generated automatically

Ada currently has no approved GitHub Actions for this purpose, and a generated snapshot would still risk becoming a second, stale truth. The lightweight automation is therefore the repository operating contract plus the PR checklist: agents must perform the continuity check and update the canonical source as part of normal work. Revisit stronger automation only if this process proves insufficient.
