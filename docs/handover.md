# Ada project handover

This file is the durable entry point for continuing Ada in a new chat or agent session.

It is deliberately **not** a project-status snapshot. Volatile facts such as current branch SHAs, open findings, test counts, active PR lists, and local scratch paths belong in their canonical sources and must be re-verified. The handover stays small by pointing to those sources instead of copying them.

Repository: https://github.com/wichtelimwald/ada

## Copy-and-paste start prompt

```text
Continue work on Ada: https://github.com/wichtelimwald/ada

Read AGENTS.md and docs/handover.md. Follow .github/skills/project-continuity.md
and .github/skills/maintainer-collaboration.md; consult only relevant task skills.
Verify main, open PRs/reviews and commit-specific validation before acting.
Continue the current task from verified state; do not reopen settled decisions
without new evidence. Work on a branch/PR; never merge without my approval.
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

## Updating this handover

Follow `.github/skills/project-continuity.md` for work-state persistence and session closeout. Change this file only if the entry routine or source-of-truth map changes; do not duplicate the contents of those sources here.

## Why this is not generated automatically

Ada currently has no approved GitHub Actions for this purpose, and a generated snapshot would still risk becoming a second, stale truth. The lightweight automation is therefore the repository operating contract plus the PR checklist: agents must perform the continuity check and update the canonical source as part of normal work. Revisit stronger automation only if this process proves insufficient.
