# Skill: Development process

Normative KISS/YAGNI workflow for developing Ada. Interaction with the maintainer is governed separately by `.github/skills/maintainer-collaboration.md`.

## Before implementation

1. Understand the actual end-to-end flow and whether a change is needed.
2. Stop at the **simplest sufficient option**, in this order:
   - Do nothing if the requirement is already met.
   - Reuse an existing repository solution or pattern.
   - Use the standard library or native platform capability.
   - Reuse an already approved dependency.
   - Evaluate credible maintained external solutions before inventing infrastructure.
   - Make the smallest local change; write custom infrastructure only when established options fail the requirements or Ada must own the trust boundary.
3. For substantive technology/dependency decisions, follow `.github/skills/technology-evaluation.md`, including the license/distribution gate, alternatives, evidence, and decision record. Do not treat a candidate mentioned in research as adopted.
4. If custom code wins over credible existing systems, document the lifetime security, privacy, licensing, maintenance, integration, and reversibility trade-off.

## During implementation

- Fix the root cause; inspect affected sibling paths. Prefer deletion to extra abstractions.
- Keep changes focused, trust boundaries explicit, and external frameworks behind Ada-owned interfaces where practical.
- Add the smallest runnable regression check for non-trivial behavior.
- Pin security- or durability-critical dependencies to reviewed versions. Update `NOTICE.md` for adopted or upgraded third-party components.
- Update an ADR and user-facing `README.md` statements when an accepted decision or relevant product behavior changes.

## Completion gate

- Validate the exact changed revision at the level appropriate to the work (documentation, tests, integration, platform checks). Report unverified paths; do not equate self-review with independent review.
- **Complexity challenge:** before calling work ready, check for unnecessary code, files, rules, dependencies, or an existing simpler mechanism.
- Do not trade away correctness, security/privacy, accessibility, recovery, or required behavior for brevity.
- For user-relevant architecture, explain in the top-level `README.md` what is accepted versus implemented, its user impact, what is reused, and what remains unverified.
