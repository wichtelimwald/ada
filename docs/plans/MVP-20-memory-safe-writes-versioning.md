# MVP-20 — Memory semantics, safe writes and versioning

Status: implementation
Roadmap: docs/product/mvp-roadmap.md
Depends on: MVP-10
Owner PR: #41

## Goal

Turn the development file-native Memory adapter into a deterministic, recoverable
authoritative write layer before protection domains are introduced in MVP-30.

## Current state / evidence

- ADR-0008 accepts Markdown/current-file authority and Git-style history as a
  compatible recovery mechanism while normal retrieval remains current-state only.
- MVP-10 already provides explicit Memory vs learning areas, seed-once personality,
  conservative promotion and a current-state forget tombstone.
- The research control under `research/memory/control/` demonstrates useful
  Markdown + Git behavior and, more importantly, the stale-write, Git-lock and
  path-scoping failures that production code must close.
- Current generic entry APIs accept semantic caller-supplied slugs, overwriting
  writes do not expose a revision token, reads still have a symlink TOCTOU window,
  directory durability is incomplete, and Git history is not wired into runtime
  writes.

## Scope

- Generate opaque random IDs for generic Memory/learning entries.
- Separate create from explicit correction; corrections keep the logical entry ID
  and require the caller's expected revision.
- Make repeated forgetting explicit and idempotent.
- Treat malformed established Memory as an integrity error and preserve it.
- Enforce area/lifecycle validity before an entry can be returned as current.
- Serialize Ada writers and detect stale same-file writes.
- Use fd-based no-follow reads and durable file + directory publication on the
  supported local POSIX profile.
- Make personality bootstrap create-only/no-clobber under concurrency.
- Record current-file changes in per-root Git history, including out-of-band human
  edits observed before Ada writes, while normal Memory reads never consult history.
- Commit only Memory paths intentionally owned by the history adapter.

## Non-goals

- Private/shared protection domains, encryption and broker authorization (MVP-30).
- Automatic learning/staleness, contradiction resolution and retrieval/RAG (MVP-40).
- Permanent historical purge/backup erasure.
- A generic force-forget API. If established Memory is malformed, MVP-20 requires
  explicit repair before ordinary forgetting; a future force path must be bound to
  a separately authorized recovery action.
- Network/distributed filesystems or Windows semantics. This slice targets the
  current local macOS/Linux profile.

## Open decisions

Resolved by ADR-0010 in this step:

1. History implementation: external Git CLI behind an Ada-owned adapter.
2. Generic identity: UUIDv4-derived opaque IDs; no semantic/time-bearing slugs.
3. Correction identity: correction updates the same logical ID and Git preserves
   prior content.
4. Concurrency contract: Ada writers serialize locally and correction uses an
   optimistic content revision; stale writes fail with a conflict instead of
   overwriting current human state.

No product/authority decision is introduced by these implementation choices.

## Reuse / dependency evidence

The existing research control already proves that Git matches the accepted history
shape. Current maintained implementation options were re-checked before coding:

- Git CLI: established external tool; GPLv2; no Python runtime dependency is added.
  `git commit --only <pathspec>` explicitly disregards staged contents for other
  paths, which matches Ada's path-restricted history requirement.
- GitPython 3.1.x: BSD-3-Clause, but still requires Git and adds Python dependencies.
- Dulwich 1.2.x: Apache-2.0 OR GPL-2.0-or-later and can avoid a Git executable, but
  adds a new runtime package and a larger Python implementation surface.
- pygit2 1.20.x: GPLv2 with linking exception and native libgit2 bindings, adding
  native distribution/review surface.

For MVP-20 the Git CLI is the KISS choice: Ada already needs Git-style semantics,
the target development environment has Git, and no extra package/native library is
required. The dependency remains replaceable behind Ada-owned code. Packaging must
revisit how Git is provisioned before a consumer release.

## Security / privacy / authority

- Git is history/recovery, not authentication, authorization or current Memory.
- Forgotten/superseded content may remain in Git history; permanent purge is a
  separate explicit operation.
- Normal load APIs read only current files.
- External Git commands run with global/system config disabled, literal pathspecs,
  fixed synthetic commit identity and no credential/network operation.
- Ada writes are serialized with a local lock; unexplained Git lock failures stop
  the operation and are never auto-deleted.
- No-follow fd reads reject symlinked files; directory roots remain restricted to
  the configured Memory root.
- Malformed current established Memory fails closed and is never silently replaced
  by a tombstone.

## Interfaces and data ownership

- `FileMemoryStore` remains the file-native adapter and authoritative current-state
  owner for this development profile.
- `GitMemoryHistory` owns only version-history capture for that root.
- `MemorySnapshot` exposes an opaque revision for safe correction; the revision is
  storage concurrency metadata, not user Memory.
- Source-owned calendar/contact/document facts remain outside this step.

## Implementation slices

1. Add the step plan and ADR-0010.
2. Add opaque ID generation, snapshot/revision and explicit correction/forget result
   semantics.
3. Harden reads/writes, locking, create-only publication and durability.
4. Add the Git history adapter and capture external edits before Ada-originated
   writes plus Ada writes immediately afterwards.
5. Add deterministic negative/concurrency/history tests and update durable docs.

## Acceptance / Definition of Done

- Create and correction are distinct APIs; a stale correction cannot overwrite a
  newer human edit.
- Generic IDs are opaque random values and a forgotten ID cannot be recreated by
  the public create APIs.
- Repeated forget returns an explicit already-forgotten result.
- Malformed established Memory remains on disk and forgetting it fails visibly.
- Invalid area/lifecycle combinations are rejected or excluded from current loads.
- Personality bootstrap cannot clobber a concurrently created profile.
- Symlinked files are rejected at open time.
- Successful writes fsync file content and the containing directory; create-only
  publication has an `O_EXCL` fallback when hard links are unavailable.
- Human edits present before an Ada write are committed separately before the Ada
  change; Ada writes are committed promptly and path-restricted.
- Git lock/history failures do not cause the Memory write to be reported as a clean
  success.
- Tests prove current reads never rehydrate from Git history.

## Validation

Required on the exact PR head before completion:

```sh
python -m unittest tests.test_file_memory
sh scripts/validate.sh
```

Target-Mac validation must additionally exercise a real Git CLI, out-of-band manual
edit capture, stale correction rejection, repeated forget and personality bootstrap
racing two processes/threads. No validation claim is made until tied to the exact
commit.

## Review focus

- Any path where a human edit can be overwritten without a revision conflict.
- Git index/pathspec leakage or hook/config execution.
- Symlink/path traversal races.
- Crash states between file publication and history commit.
- History accidentally influencing current retrieval.
- Semantic IDs or sensitive content in tombstone/reference metadata.

## Follow-ups

- MVP-30 owns encrypted per-domain history and broker-enforced protection domains.
- MVP-40 owns automatic lifecycle transitions, contradiction/currentness resolution
  and derived retrieval.
- Packaging must decide how Git is provisioned for non-developer installations.
