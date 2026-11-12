# MVP-30 — User- and audience-scoped Memory access

Status: implementation, redesigned 2026-11-12
Roadmap: docs/product/mvp-roadmap.md
Depends on: MVP-20
Decision: docs/decisions/ADR-0012-memory-access-mvp-boundary.md
Prior work: S1 #46 merged; native macOS isolation probes #47 archived as research

## Goal

Ada must only use, retrieve, update and disclose Memory and source material
authorized for the trusted actor, intended audience and requested operation.
The enforcement boundary is Ada's trusted application APIs, **not** a new
macOS storage-encryption or same-user process-isolation system.

## Agreed constraints

- Preserve file-native, Markdown-first, human-editable authoritative Memory,
  established/learning separation and Git-style edit history (ADR-0008/0010).
- Keep personal scopes private by default and family sharing explicit. Neither
  model text nor caller-supplied scope/path/domain IDs grant permissions.
- Bind trusted actor/audience/authorization context in AdaGuard/application
  logic and fail closed on unknown, missing or ambiguous scope.
- Apply the same checks to reads, retrieval/context, writes, disclosure,
  source/document providers and rebuildable derived indexes.
- Keep the model away from unrestricted filesystem and source-provider tools.
  A resolved MemoryScope is not a bearer authorization token.
- No MVP requirement for a host broker process, Keychain vault integration,
  per-person encrypted disk images, separate Mac account/system daemon,
  VM-to-host IPC, or encryption of Memory and Git history by Ada.
- Explicit residual: same-user host applications and fully compromised
  Ada code may read files accessible to that macOS user. The Mac owner
  supplies host encryption, account isolation, backup and sync controls.
- Do not connect real family Memory until actor binding, scope checks and
  required downstream privacy/learning controls are validated.

## Evidence / reuse

S1 in PR #46 implements MemoryAccessContext, MemoryBrokerPort and a
fail-closed in-memory domain contract; preserve it if useful as a logical
scope adapter, without interpreting it as a production process boundary.
ADR-0011's stronger topology is superseded by ADR-0012. Native Mac A/B/C
probes in PR #47 remain archival research, not required S2 acceptance.

MVP-20 FileMemoryStore/GitMemoryHistory still operate on one Memory root.
Git configuration/attribute execution safety and the late concurrent
non-cooperating human save remain real follow-ups independent of encryption.

## Identity and integration boundary

The **restricted MVP admin chat** establishes and changes permissions. It
requires a trusted administrator, never model output, forwarded email or a
generic unverified chat turn. How that local administrative authority is
verified and bound to AdaGuard is a concrete implementation gate for the
admin-chat slice, **not** permission for the model to edit policies.

For MVP-30, establish a small application-level contract for **already
trusted** actor, intended audience, action and grant, then integrate that
with the existing AdaGuard and Memory APIs. MVP-30 does **not** decide how
email sender authentication works: MVP-70 will verify registered real sender
addresses and supply trusted context, failing closed before live side effects.

The maintainer explicitly prefers **learning by doing** with actual family
participants and non-sensitive calendar appointments, **not fake family
identities or a synthetic household as a product acceptance substitute**.
Continue deterministic regression tests of API/permission invariants; those
are not evidence that the live email-calendar flow is ready. Pilot only
after mail authentication, grants, duplicate prevention and recovery work.
The family calendar is the first vertical milestone; generalized Memory
learning is not a prerequisite for that calendar pilot.

General user chat remains post-MVP. The restricted admin chat is a separate
function; the current development CLI chat must not implicitly become an
administrator.

## Next implementation question

What is the smallest reuse of AdaGuard and the S1 scope contract that
enforces permissions for an **already verified actor/audience** without
another service or parallel authorization engine?

## Implementation slices

### S1 — Existing scoping contract (merged #46)

Retain opaque logical domain references and fail-closed contract tests as
infrastructure, not proof of per-user storage isolation.

### S2 — Policy-scoped reads and context

Bind an already trusted actor, intended audience and AdaGuard grant to the
existing Memory access path; reuse S1 only where it helps. Prove the
scope enforcement, including deny-by-default and no model/quoted escalation,
with deterministic checks. End-to-end audience validation uses actual
registered users after MVP-70 establishes their email identity; do not
create simulated people as a substitute for that pilot.

### S3 — Scoped writes, sources and history

Carry the same scope through corrections, forgetting, promotion and source
providers. Preserve MVP-20 history/currentness and protect Git commands
from untrusted repo-local config/attributes. No generic model file tools.

### S4 — Concurrency, recovery and end-to-end acceptance

Resolve/document ADR-0010's last late human-save race, including an honest
evaluation of separate worktrees vs normal uncooperative editor saves.
Validate restart, history and operator-owned backup/restore.
Review missing identity, cross-scope denial, safe sharing, derived retrieval
and disclosed responses. For the initial calendar milestone, use the actual
registered family accounts and non-sensitive test events only after the email
and admin-grant gates are implemented. Update threat/privacy docs.

## Definition of done

Authorized personal data cannot be read, searched, modified or disclosed
through Ada to another registered user without a corresponding grant.
Validate the end-to-end behavior with actual registered users on
non-sensitive pilot records; keep deterministic unauthorized-scope
regressions but do not treat simulated identities as the MVP pilot.
Shared access is scoped; unavailable identity/grants fail closed.
The model cannot mint an authorization or access filesystem bypasses.
Current Markdown and edit history remain correct across restart; Git
executable-metadata safety, concurrency residual and backup responsibilities
are addressed. User docs make no OS isolation/encryption claims.
Exact-head tests and independent review are required.

## Validation

Existing: python -m unittest tests.test_memory_broker_contract
Existing: python -m unittest tests.test_architecture_boundaries
Repository: sh scripts/validate.sh

These S1 checks do not validate end-to-end authorization. Preserve
deterministic allow/deny regression coverage and verify the actual
registered-user flow later, once MVP-70 sender authentication and the
MVP admin-chat grant interface are available. No real user data or
calendar side effects are part of this documentation change.
