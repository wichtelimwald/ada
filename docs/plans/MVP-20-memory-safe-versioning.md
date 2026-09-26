# MVP-20 — Memory semantics, safe writes and versioning

Status: implementation
Roadmap: docs/product/mvp-roadmap.md
Depends on: MVP-10
Owner PR: pending

## Goal

Turn the development-only file-native Memory adapter into a deterministic,
recoverable write/versioning layer that preserves human edits and rejects
ambiguous concurrent writes before protection domains are added in MVP-30.

## Current state / evidence

MVP-10 provides current Markdown authority, separate `memory/` and `learning/`
areas, seed-once personality, conservative promotion, and current-state
forgetting. The remaining gaps are the MVP-20 items in the roadmap and
`docs/todo.md`: semantic create/correct/forget behavior, opaque immutable IDs,
currentness validation, edit capture/history, concurrency, crash durability,
no-follow file access, and create-only publication without hard links.

ADR-0008 already accepts Markdown as authority and Git-style per-domain history
as the leading MVP versioning adapter, while keeping history out of normal
Memory retrieval.

## Scope

- Generate opaque random IDs for new generic Memory/learning entries; callers do
  not choose semantic IDs.
- Define create separately from correction. Correction keeps the stable entry
  identity, requires the revision the caller read, and fails on a stale revision
  instead of using last-write-wins.
- Treat malformed established Memory as an integrity failure. Normal forget does
  not overwrite or remove a malformed established file.
- Return explicit forget outcomes: forgotten, already forgotten, or not found.
  Forgotten IDs remain reserved and cannot be reused.
- Enforce area/lifecycle currentness before established Memory is returned as
  current context.
- Capture direct human edits into Git-style history before Ada consumes or
  changes them.
- Record Ada writes as separate history revisions without reading history back
  into current Memory.
- Serialize local mutations with an OS advisory lock and use revision checks to
  reject stale same-file corrections.
- Use fd-based no-follow reads, atomic replacement, create-only O_EXCL
  publication, file durability, and parent-directory durability for the
  supported local macOS/Linux storage profile.
- Make personality bootstrap create-only under concurrency.

## Non-goals

- Protection-domain authorization, encryption, or the Memory Broker (MVP-30).
- Automatic learning/retention/staleness policies and generic model-facing
  writes (MVP-40).
- Derived search/RAG.
- Historical purge/backup policy.
- Network/distributed filesystems whose fsync/locking semantics differ from the
  supported local filesystem profile.
- Automatic semantic conflict resolution between two different explicit claims.

## Open decisions

No product decision is intentionally left open inside MVP-20. The versioning
adapter choice is documented in ADR-0009 in this work package. If implementation
evidence invalidates that choice, stop and revise the ADR rather than growing a
second history mechanism.

## Reuse / dependency evidence

The existing research control proved the useful semantics of local Git history
and exposed unsafe unscoped staging, stale locks, and stale-write behavior, but
it shells out to the Git executable. Ada's runtime image does not install Git.

Options for the runtime adapter:

1. **Dulwich** — standalone Git implementation for Python; no Git executable is
   required. Version 1.2.15 supports Python 3.14 and is dual-licensed
   Apache-2.0 OR GPL-2.0-or-later; Ada uses it under Apache-2.0. Its required
   `urllib3>=2.2.2` dependency is MIT. Security fixes published through
   Dulwich 1.2.12 cover the 2026 checkout/path issues, so 1.2.15 is the minimum
   reviewed version for this decision.
2. **System Git subprocess** — mature and already characterized by the research
   control, but would add a system executable/package to Ada's runtime image and
   require subprocess/environment hardening.
3. **pygit2/libgit2** — mature Git implementation but adds native libgit2
   packaging and a larger platform/distribution surface for a small local
   history use case.
4. **Custom snapshot/history format** — rejected because Git-style history is
   already accepted and custom version-control infrastructure would add
   unnecessary recovery/security work.

Decision: use Dulwich behind an Ada-owned history adapter. Keep the authoritative
Markdown format independent from Dulwich.

## Security / privacy / authority

- Current Markdown remains the only semantic Memory authority.
- History is recovery/versioning state, never a source for model context,
  retrieval, promotion, or forgotten-content rehydration.
- History may retain earlier sensitive content until a separate purge policy is
  implemented; this is the already accepted ADR-0008 forgetting split.
- The history adapter records only `memory/*.md` and `learning/*.md`; it does
  not stage arbitrary files.
- Direct edits are untrusted as Git identity evidence. Their content is still
  human-authoritative current file state, subject to schema/integrity checks.
- Malformed current files are captured for recovery and then rejected visibly.
- OS locks coordinate Ada processes but do not prevent a human editor from
  changing a file. Revision checks and pre/post snapshots detect that race.
- No secrets or real household data are used in tests.

## Interfaces and data ownership

- `FileMemoryStore` owns current-file semantics.
- An Ada-owned history adapter owns Git-style revisions only.
- Generic entry IDs are stable opaque identifiers; human meaning remains in
  Markdown content.
- A versioned load returns the current entry plus a content revision token used
  for optimistic concurrency.
- Personality remains a separate reserved Ada-owned file.

## Implementation slices

1. Add semantic result/version types, opaque ID generation, lifecycle checks,
   create/correct/forget semantics, and deterministic tests.
2. Harden file I/O and locking: no-follow fd reads, atomic/create-only writes,
   file + directory durability, and create-only personality bootstrap.
3. Add the Dulwich-backed per-root history adapter with external-edit capture and
   Ada-write revisions; prove normal loads never rehydrate history.
4. Add concurrency/crash/error tests, update user-facing README/backlog/NOTICE,
   and run full project validation.

## Acceptance / Definition of Done

- New generic IDs are opaque random IDs and are not caller-selected semantic
  slugs.
- A stale correction cannot overwrite a manual or concurrent correction.
- Create cannot overwrite an existing or historically used ID.
- Malformed established Memory survives forget attempts unchanged and fails
  visibly.
- Repeated forget returns `already_forgotten`; a missing ID returns
  `not_found`.
- Only valid current established lifecycle state is returned by normal Memory
  loads.
- A direct Markdown edit is committed to history before it is returned/changed
  by Ada.
- A forgotten/deleted current file is never reconstructed by a normal load even
  though history retains it.
- Personality bootstrap cannot clobber an existing concurrent seed.
- Deterministic tests cover no silent overwrite, stale re-promotion, history
  rehydration, lost human correction, and ambiguous write outcomes.
- Full `sh scripts/validate.sh` passes on the exact PR head. Target-macOS
  validation is recorded before merge if it cannot be run in the implementation
  environment.

## Validation

- `sh scripts/validate.sh`
- Focused `python -m unittest tests.test_file_memory tests.test_personality_bootstrap -v`
- Tests simulate stale revision, direct edit, malformed established Memory,
  repeated forget, history-only old content, concurrent bootstrap, no-follow
  rejection, and history failure.
- Before merge, validate on the supported target Mac because the storage profile
  includes macOS advisory locking and durability behavior.

## Review focus

- Any path where history can become semantic current Memory.
- TOCTOU/symlink escape around reads/writes/history scanning.
- Lost-update windows between revision check, write, and history commit.
- Whether malformed Memory can be destroyed by forget/recovery behavior.
- Whether an Ada history commit can absorb an unrelated concurrent human edit.
- Crash points that could leave current state written but history outcome
  ambiguous.
- Dulwich license/transitive surface and reviewed-version pin.

## Follow-ups

Protection domains/encryption remain MVP-30. Learning validation/retrieval and
model-facing writes remain MVP-40. Historical purge/backup policy remains a
separate operations/privacy concern.
