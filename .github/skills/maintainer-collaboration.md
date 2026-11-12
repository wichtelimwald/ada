# Maintainer collaboration — situational details

The **always-on** collaboration rules are in `AGENTS.md`. This file adds task-level practices for development agents; it does not define Ada's persona, runtime skills, or security policy.

## Decisions

- For a material choice, identify the next question whose prerequisites are known. Present the recommended default and its decisive trade-off; ask one question, then reconsider based on the answer.
- Do not turn a discussion into a project plan unless the maintainer requests one. Avoid interviewing for trivial, obvious, or reversible details.
- For detailed technology evaluation and weighted decisions, follow `.github/skills/technology-evaluation.md`; do not invent weights or scores.

## Execution and correction

- Once a task is authorized, complete the reasonable implementation, validation, and PR follow-up without asking for the same permission again. **Merge authorization remains separate.**
- Substantiate review findings before fixing them; inspect the affected class of cases, and prefer a coherent correction/validation pass over repeated micro-runs.
- When the maintainer must run commands locally, give one complete copy-and-paste block and request one batch of results.
- For `/eli5`, use a concrete example and simpler language without changing the technical meaning.

## Delegation, if approved

- Give a worker a bounded scope, relevant interfaces and constraints, a complete ready-to-use prompt, and a recommended target model.
- Inspect the worker's actual changes and rerun decisive checks. A worker's completion claim is not independent verification or maintainer acceptance.

## Reporting

- Name the exact verified revision, checks and remaining uncertainty. Do not equate a proposal, passing CI, a review, a merge, and explicit user acceptance.
- Preserve uncommitted work. Keep PR findings and their resolutions on the PR; use `.github/skills/project-continuity.md` for durable state.
