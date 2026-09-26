# Ada step-plan process

This directory contains execution plans for individual roadmap work packages.

Canonical MVP ordering and dependencies live in
`docs/product/mvp-roadmap.md`. General backlog items live in `docs/todo.md`.
ADRs own accepted architectural decisions.

## Starting a roadmap step

When a maintainer asks an agent to implement a roadmap step:

1. Re-verify `main`, open PRs, unresolved reviews, and the roadmap.
2. Select the step using the selection contract in
   `docs/product/mvp-roadmap.md`.
3. Read the step's relevant ADRs, product scenarios, security/privacy docs, and
   backlog items.
4. Search for credible maintained reuse candidates before designing custom
   infrastructure when the step introduces a new substantial capability.
5. Create a branch. Never work directly on `main`.
6. Create or update one plan file:
   `docs/plans/<STEP-ID>-<short-slug>.md`.
7. Resolve decision-relevant unknowns. Create/revise an ADR when required.
8. Implement the smallest end-to-end slices from the plan.
9. Validate against the plan's acceptance criteria and repository validation.
10. Record independent review findings in the PR and reproduce findings before
    changing code.
11. Persist residual follow-ups in `docs/todo.md`; do not leave important work
    only in PR comments.
12. Mark the roadmap package `done` only when the implementation PR itself is
    complete, reviewed, validated, and ready for maintainer-authorized merge.
13. Never merge without explicit maintainer authorization.

A plan may evolve during implementation. It should remain concise enough to be
read by the next agent.

## Required plan structure

Use this structure unless a step clearly does not need one of the sections.

```markdown
# <STEP-ID> — <title>

Status: planning | implementation | review | complete
Roadmap: docs/product/mvp-roadmap.md
Depends on: <step ids>
Owner PR: <PR once created>

## Goal
What user/project outcome becomes possible?

## Current state / evidence
What already exists? Which ADRs, tests, ports, prior research and merged PRs are
relevant?

## Scope
Concrete behaviors delivered by this step.

## Non-goals
What is deliberately deferred?

## Open decisions
Only material decisions that still block or shape implementation.

## Reuse / dependency evidence
Existing maintained options, license/security/platform fit, and why reuse/adapt/
build is chosen.

## Security / privacy / authority
Trust boundaries, data classes, identities/audiences, egress, secrets, side
effects and failure modes.

## Interfaces and data ownership
Ada-owned ports/types and which system remains authoritative for each fact.

## Implementation slices
Small ordered vertical slices. Each should be independently testable.

## Acceptance / Definition of Done
Observable pass/fail criteria, including representative scenarios.

## Validation
Commands, target platforms, negative tests, crash/retry tests where relevant.

## Review focus
Specific risks an independent reviewer should attack.

## Follow-ups
Only items explicitly outside the step. Before merge, durable follow-ups must
also be copied to docs/todo.md.
```

## Parallel work

Parallel work is encouraged only through stable boundaries.

- Two steps may proceed in parallel when both are `ready` in the roadmap and
  they do not modify the same unresolved authority/data-ownership decision.
- Each step gets its own branch and PR.
- If one step discovers a cross-cutting decision that invalidates another step's
  assumptions, stop and reconcile the shared ADR/interface rather than creating
  divergent local conventions.
- A skipped "next" step remains pending; completing a later independent step must
  not silently mark its dependency complete.
