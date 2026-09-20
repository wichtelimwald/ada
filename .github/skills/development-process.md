# Skill: Development process

This is Ada's normative KISS/YAGNI development workflow.

## Before implementation

1. Understand the end-to-end user and system flow.
2. Ask whether the change is needed at all.
3. **Survey existing solutions before designing custom infrastructure.**
   - Check standard/platform capabilities.
   - Check already-approved Ada dependencies.
   - Search credible, maintained purpose-built libraries/frameworks/services for the problem domain.
   - Check relevant reference systems where licensing/clean-room rules permit.
   - If a new credible candidate appears that could materially change a decision, reopen the comparison before accepting an ADR.
4. **Run the license/distribution gate for every serious candidate before scoring it as viable.**
   - Record code/runtime/server/SDK licenses separately where they differ.
   - Check model, weight, voice, dataset and asset licenses separately.
   - Check hosted-service/usage restrictions, commercial-use restrictions, copyleft/network-copyleft, attribution/NOTICE, trademark, redistribution and bundled/transitive artifacts.
   - Confirm compatibility with Ada's MIT-owned code, intended self-hosted distribution and likely future deployment modes.
   - Non-OSI licenses such as BSL are not an automatic rejection, but their restrictions must be an explicit decision factor.
5. Prefer an established solution when it satisfies the requirements and can be kept behind an Ada-owned boundary.
6. Prefer standard/platform capabilities over adding another dependency when they solve the same problem adequately.
7. Reuse an already-approved dependency where appropriate.
8. Build custom infrastructure only when the evaluated alternatives do not fit, or when Ada must own the semantics/trust boundary itself.
9. Choose the smallest change that satisfies the requirement.

A custom implementation is not the default control winner. If custom code is selected over credible existing systems, document why the lifetime security, privacy, licensing, maintenance, integration, and replaceability trade-off is better.

## Architecture / decision gate

For a non-trivial technology choice:

1. Define requirements and hard gates.
2. Identify credible existing systems **before** finalizing the candidate set.
3. Check licenses and distribution constraints.
4. Agree decision criteria/weights where appropriate.
5. Gather current evidence and run only decision-changing prototypes.
6. Re-score if prototype evidence changes an important assumption.
7. Record the accepted choice, consequences, fallback/re-open triggers, and dependency license status in the ADR.
8. If the decision changes user-visible trust, privacy, permissions, recovery, autonomy, data handling, or product behavior, update the top-level README in plain language in the same decision/implementation sequence.

## During implementation

- Fix root causes, not symptoms.
- Keep diffs focused.
- Make trust boundaries explicit.
- Keep third-party frameworks behind Ada-owned ports/types where practical.
- Add the smallest useful runnable verification for non-trivial behavior.
- Update an ADR when implementation changes a documented architectural decision.
- Pin security- or durability-critical dependencies to reviewed versions.
- Update `NOTICE.md` when a third-party component is adopted or upgraded.

## Completion gate

Do not claim completion without concrete validation evidence appropriate to the current project phase. Never trade away security, privacy, accessibility, error handling, data-loss protection, or license compliance to reduce code size.

For user-relevant architecture work, completion also requires a concise README statement that distinguishes:

- what is already accepted/implemented;
- what protection or behavior the user gets;
- which established component Ada reuses;
- what remains under evaluation or not yet implemented.
