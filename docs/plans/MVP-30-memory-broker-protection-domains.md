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

## Identity binding — next implementation gate

The maintainer confirmed **email-only** family interaction for the MVP on
2026-11-12. A registered sender address maps to a configured actor only after
MVP-70 validates the sender beyond the forgeable visible `From:` header.
The intended recipient/audience must be bound from trusted mail routing and
configured permissions; it is not authority by itself. Forwarded text or a
model cannot impersonate that sender or expand scope. Reject unverifiable
identity and missing/ambiguous audience. The next concrete design question is
what verifiable inbound authentication evidence the selected email provider
exposes, and what fail-closed behavior applies when evidence is absent.

The native chat CLI remains only a development harness. A future chat login
may use an emailed one-time code and/or passkey, outside MVP-30. No broad/new
privileges are granted by ordinary incoming email; stronger approval methods
remain a separate product/security gate.

## Implementation slices

### S1 — Existing scoping contract (merged #46)

Retain opaque logical domain references and fail-closed contract tests as
infrastructure, not proof of per-user storage isolation.

### S2 — Policy-scoped reads and context

Bind authenticated actor, intended audience and applicable AdaGuard grant
to the existing Memory access path. Use S1's contract where it helps.
Validate direct reads, search and model-context construction for two
synthetic private people and one shared audience. Deny model/quoted
instructions that try to widen scope.

### S3 — Scoped writes, sources and history

Carry the same scope through corrections, forgetting, promotion and source
providers. Preserve MVP-20 history/currentness and protect Git commands
from untrusted repo-local config/attributes. No generic model file tools.

### S4 — Concurrency, recovery and end-to-end acceptance

Resolve/document ADR-0010's last late human-save race, including an honest
evaluation of separate worktrees vs normal uncooperative editor saves.
Validate restart, history and operator-owned backup/restore.
Review identity ambiguity, cross-scope denial, safe sharing, derived
retrieval and disclosed responses. Update threat/privacy docs accordingly.

## Definition of done

Synthetic A-private cannot be read, searched, modified or disclosed through
Ada by B or a family-shared context without an explicit grant. Shared access
is audience-scoped and minimal; unavailable identity/grants fail closed.
The model cannot mint an authorization or access filesystem bypasses.
Current Markdown and edit history remain correct across restart; Git
executable-metadata safety, concurrency residual and backup responsibilities
are addressed. User docs make no OS isolation/encryption claims.
Exact-head tests and independent review are required.

## Validation

Existing: python -m unittest tests.test_memory_broker_contract
Existing: python -m unittest tests.test_architecture_boundaries
Repository: sh scripts/validate.sh

These S1 checks do not yet validate end-to-end authorization. Implement
new synthetic positive/negative tests alongside scoped integration.
