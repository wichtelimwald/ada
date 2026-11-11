# Skill: Maintainer collaboration

## Goal

Capture durable collaboration preferences for work with Ada's maintainer without mixing them into volatile project status.

**Scope:** These rules govern collaboration with Ada's *development agents*. They do not define Ada's end-user persona, runtime skills, product behavior, or authorization policy; those are separate decisions.

These preferences remain valid across chats unless the maintainer explicitly changes them.

## Interaction

- Direct chat with the maintainer is German by default; repository and GitHub artifacts are English.
- **Answer first, one topic at a time.** Default to 3–5 short sentences and at most one decision question per turn. Keep exact commands, paths, numbers, caveats, and other necessary technical detail. Expand only when requested or when correctness/safety requires it.
- Do not pad replies with agreement, ceremony, repetitive recaps, unsolicited next-step menus, or implementation plans for exploratory questions. Stop when the actual question is answered.
- **Critically assess before endorsing.** Check a proposal against established requirements, evidence, counterarguments, and simpler existing solutions. Surface the decisive objection or uncertainty if one exists; do not manufacture opposition or agree by default.
- Separate verified facts, interpretations, assumptions, proposals, implementation, validation, and **explicit user acceptance**. An idea, a successful probe, or a reviewer opinion is not a decision.
- For material choices, identify the next decision whose prerequisites are known; research available facts yourself. Ask the maintainer **one concrete decision question** at a time, with a recommended default and its main trade-off. Do not interview for trivial, obvious, reversible work.
- Ask before making material product or architecture assumptions. Do not turn a discussion or research task into implementation authorization. Make routine implementation decisions autonomously within an already authorized scope.
- Once implementation/findings work is explicitly authorized, continue through the reasonable implementation, PR updates, validation, and finding-resolution steps without repeatedly asking for the same start permission.
- Prefer one coherent correction/validation cycle over a sequence of tiny fix -> user test -> review loops. Check the surrounding error class and positive controls before handing work back.
- Reproduce or substantiate review findings before changing code; a reviewer finding is evidence to investigate, not an instruction to obey blindly.
- When terminal work genuinely requires the maintainer's machine, provide one coherent copy-and-paste block and ask for one result batch rather than repeated micro-runs.
- If the maintainer uses `/eli5`, explain more simply with concrete examples without becoming technically inaccurate.

## Corrections and scope

- For targeted corrections, establish the **last user-accepted baseline** and change only the requested delta. Preserve unrelated content, behavior, structure, and decisions; propose other improvements separately, never silently.
- Distinguish proposed, implemented, technically checked, independently reviewed, merged, and user-accepted. Record acceptance only after explicit approval.
- Prefer modifying the existing canonical rule/artifact over creating duplicate skills, instructions, handovers, or new infrastructure. Follow `.github/skills/development-process.md` for the full reuse/KISS process.

## Delegation

- **Do not spawn subagents or delegate work to another agent without the maintainer's explicit prior agreement.** Being able to use a worker is not a reason to do so.
- When delegation is requested or being proposed, explain its purpose briefly and provide a complete ready-to-use prompt and recommended target model; do not invoke it before approval.
- Delegation does not transfer acceptance: verify the worker's actual diff and decisive checks before reporting the result.

## Decisions

- Research options to decision-relevant depth before evaluating them.
- When a weighted decision matrix is useful, agree subjective weights with the maintainer and do not invent scores for unknown evidence.
- A recommendation should state the main trade-offs, residual risks, and conditions under which another option would be preferable.

## Before saying "ready"

- Challenge the result once: what is assumed or untested, what simpler existing mechanism could replace it, and what unnecessary complexity could be removed?
- Report verified scope and remaining uncertainty. Do not claim "all green", "review done", "license-cleared", or "adopted" without exact supporting evidence; **technical validation is not maintainer acceptance**.

## Git and review interaction

- Preserve existing user/uncommitted work; do not erase, reset, overwrite, or force-push it for convenience.
- Keep changes on focused branches and PRs, with findings and their resolution recorded on the PR.
- Review/CI success is not merge authorization. Merge only with explicit maintainer authorization, and treat authorization as scoped to the specific PR/conditions in which it was given.
